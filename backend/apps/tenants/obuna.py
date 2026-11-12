"""Obuna to'lovlari tarixi: so'rov (rahbar «to'ladim» dedi yoki chek yubordi) → egasining qarori → muddat uzayadi.

Har to'lov bitta qator (`ObunaTolovi`). Qator o'chirilmaydi: xato kiritilgan to'lov «bekor qilingan» bo'lib qoladi
va muddat avvalgi sanaga qaytadi. Pul kelganini faqat platforma egasi tasdiqlaydi (panel yoki botdagi tugma).
"""
import calendar

from django.db import transaction
from django.utils import timezone

from .models import ObunaTolovi, Salon

H = ObunaTolovi.Holat
MAKS_OY = 24
MAKS_SUMMA = 10 ** 10


class ObunaXatosi(Exception):
    pass


def keyingi_muddat(salon, oylar, bugun=None):
    """Muddat hali tugamagan bo'lsa undan, tugagan bo'lsa bugundan boshlab `oylar` oyga uzaytirilgan sana."""
    bugun = bugun or timezone.localdate()
    asos = max(salon.obuna_muddati() or bugun, bugun)
    yil, oy = asos.year + (asos.month - 1 + oylar) // 12, (asos.month - 1 + oylar) % 12 + 1
    return asos.replace(year=yil, month=oy, day=min(asos.day, calendar.monthrange(yil, oy)[1]))


def standart_summa(salon, oylar):
    return (salon.tarif.oylik_narx if salon.tarif_id else 0) * oylar


def _rahbarlarga(salon, matn, kalit):
    """Qaror haqida salon rahbarlariga Telegram xabar. Xabar xatosi to'lovni buzmaydi."""
    def yubor():
        try:
            from apps.notify.services import rahbarlarga
            rahbarlarga(salon, 'obuna_tolovi', matn, kalit=kalit)
        except Exception:  # noqa: BLE001
            pass
    transaction.on_commit(yubor)


def tolov_sorovi(salon, xodim=None, chek_fayl='', chek_tur='', izoh=''):
    """Rahbar to'laganini bildirdi. Salonda bitta ochiq so'rov bo'ladi: chek keyin kelsa — o'shanga biriktiriladi
    (ikki so'rov ikki marta qabul qilinib, muddat ikki marta uzayib ketmasin)."""
    t = ObunaTolovi.objects.filter(salon=salon, holat=H.KUTILMOQDA).order_by('-id').first()
    if not t:
        return ObunaTolovi.objects.create(salon=salon, xodim=xodim, manba=ObunaTolovi.Manba.BOT, chek_fayl=chek_fayl,
                                          chek_tur=chek_tur, izoh=izoh[:300])
    if chek_fayl:
        t.chek_fayl, t.chek_tur = chek_fayl, chek_tur
    if izoh:
        t.izoh = izoh[:300]
    t.xodim = xodim or t.xodim
    t.save(update_fields=['chek_fayl', 'chek_tur', 'izoh', 'xodim'])
    return t


@transaction.atomic
def tolov_qabul(salon_id, oylar, kim, tolov_id=None, summa=None, manba=ObunaTolovi.Manba.PANEL):
    """To'lovni qabul qiladi: tarixga yoziladi va obuna `oylar` oyga uzayadi. `tolov_id` — kutayotgan so'rov."""
    if not 1 <= oylar <= MAKS_OY:
        raise ObunaXatosi(f"Oy soni 1 dan {MAKS_OY} gacha bo'lishi kerak.")
    s = Salon.objects.select_for_update(of=('self',)).select_related('tarif').filter(id=salon_id).first()
    if not s:
        raise ObunaXatosi('Salon topilmadi.')
    if tolov_id is None:
        t = ObunaTolovi(salon=s, manba=manba)
    else:
        t = ObunaTolovi.objects.select_for_update().filter(id=tolov_id, salon=s).first()
        if not t:
            raise ObunaXatosi("To'lov so'rovi topilmadi.")
        if t.holat != H.KUTILMOQDA:
            raise ObunaXatosi(f"Bu so'rov bo'yicha qaror qabul qilingan: {t.get_holat_display().lower()}.")
    summa = standart_summa(s, oylar) if summa is None else summa
    if not 0 <= summa <= MAKS_SUMMA:
        raise ObunaXatosi("Summa noto'g'ri.")
    t.holat, t.oylar, t.summa = H.QABUL, oylar, summa
    t.eski_obuna, t.yangi_obuna = s.obuna_tugaydi, keyingi_muddat(s, oylar)
    t.qaror_vaqt, t.qaror_kim = timezone.now(), kim[:64]
    t.save()
    s.obuna_tugaydi = t.yangi_obuna
    s.save(update_fields=['obuna_tugaydi'])
    s.obunani_yangila()
    from apps.notify.services import som
    _rahbarlarga(s, f"✅ {s.nomi}: obuna {t.yangi_obuna:%d.%m.%Y} gacha uzaytirildi ({oylar} oy"
                 + (f', {som(summa)}' if summa else '') + ').', f'obuna-tolov:{t.id}:qabul')
    return t


@transaction.atomic
def tolov_rad(tolov_id, kim):
    t = ObunaTolovi.objects.select_for_update(of=('self',)).select_related('salon').filter(id=tolov_id).first()
    if not t:
        raise ObunaXatosi("To'lov so'rovi topilmadi.")
    if t.holat != H.KUTILMOQDA:
        raise ObunaXatosi(f"Bu so'rov bo'yicha qaror qabul qilingan: {t.get_holat_display().lower()}.")
    t.holat, t.qaror_vaqt, t.qaror_kim = H.RAD, timezone.now(), kim[:64]
    t.save(update_fields=['holat', 'qaror_vaqt', 'qaror_kim'])
    _rahbarlarga(t.salon, f"⚠️ {t.salon.nomi}: obuna to'lovi tasdiqlanmadi — pul kelgani ko'rinmadi. "
                 "Platforma egasi bilan bog'laning.", f'obuna-tolov:{t.id}:rad')
    return t


@transaction.atomic
def tolov_bekor(tolov_id, kim):
    """Xato qabul qilingan to'lovni bekor qiladi: muddat avvalgi sanaga qaytadi. Faqat salonning oxirgi to'lovi."""
    t = ObunaTolovi.objects.select_for_update().filter(id=tolov_id).first()
    if not t:
        raise ObunaXatosi("To'lov topilmadi.")
    if t.holat != H.QABUL:
        raise ObunaXatosi("Faqat qabul qilingan to'lov bekor qilinadi.")
    s = Salon.objects.select_for_update().get(id=t.salon_id)
    oxirgi = ObunaTolovi.objects.filter(salon=s, holat=H.QABUL).order_by('-qaror_vaqt', '-id').first()
    if oxirgi.id != t.id:
        raise ObunaXatosi("Faqat salonning oxirgi to'lovi bekor qilinadi.")
    if s.obuna_tugaydi != t.yangi_obuna:
        raise ObunaXatosi("Obuna sanasi shu to'lovdan keyin qo'lda o'zgartirilgan — sanani o'zingiz tuzating.")
    t.holat, t.bekor_vaqt, t.bekor_kim = H.BEKOR, timezone.now(), kim[:64]
    t.save(update_fields=['holat', 'bekor_vaqt', 'bekor_kim'])
    s.obuna_tugaydi = t.eski_obuna
    s.save(update_fields=['obuna_tugaydi'])
    s.obunani_yangila()
    muddat = s.obuna_muddati()
    _rahbarlarga(s, f"⚠️ {s.nomi}: obuna to'lovi bekor qilindi (xato kiritilgan edi). "
                 + (f"Muddat: {muddat:%d.%m.%Y}." if muddat else ''), f'obuna-tolov:{t.id}:bekor')
    return t


def summa_ozgartir(tolov_id, summa):
    """Qabul qilingan to'lov summasini tuzatadi (botdan qabul qilinganda summa tarifdan olinadi)."""
    t = ObunaTolovi.objects.filter(id=tolov_id).first()
    if not t:
        raise ObunaXatosi("To'lov topilmadi.")
    if t.holat != H.QABUL:
        raise ObunaXatosi("Faqat qabul qilingan to'lov summasi o'zgartiriladi.")
    if not 0 <= summa <= MAKS_SUMMA:
        raise ObunaXatosi("Summa noto'g'ri.")
    t.summa = summa
    t.save(update_fields=['summa'])
    return t


def tolov_json(t):
    return {'id': t.id, 'salon': t.salon_id, 'yaratilgan': t.yaratilgan, 'holat': t.holat, 'manba': t.manba,
            'oylar': t.oylar, 'summa': t.summa, 'eski_obuna': t.eski_obuna, 'yangi_obuna': t.yangi_obuna,
            'izoh': t.izoh, 'chek': bool(t.chek_fayl), 'xodim': t.xodim.ism if t.xodim_id else '',
            'qaror_vaqt': t.qaror_vaqt, 'qaror_kim': t.qaror_kim, 'bekor_vaqt': t.bekor_vaqt, 'bekor_kim': t.bekor_kim}
