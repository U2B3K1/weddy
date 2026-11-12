"""Xabarnomalar: rahbarga so'rov va ogohlantirishlar, sotuvchiga eslatmalar (4.14, 7.2).

Asosiy qoida: xabar yuborishdagi har qanday xato asosiy amalni (zakaz, to'lov, chegirma) hech qachon buzmaydi.
"""
import base64
import hashlib
import hmac
import logging
import secrets
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.tenants.models import Ariza, IshonchliQurilma, Salon, Xodim, jurnalga_yoz, platforma_sozlama
from apps.tenants.permissions import salon_yoza_oladimi

from . import telegram
from .models import KirishKodi, TelegramUlash, Xabar

log = logging.getLogger(__name__)

ULASH_MUDDATI = timedelta(minutes=15)
KIRISH_KODI_MUDDATI = timedelta(minutes=5)
KIRISH_KODI_URINISH = 5
JIM_TURLAR = {'yangi_zakaz'}  # ovozsiz yuboriladi: arxiv uchun, hech kimni bezovta qilmasin

# Xodim botda o'zi yoqib-o'chira oladigan xabar guruhlari: kalit → (nom, xabar turlari, shu guruhni oladigan rollar).
# Ro'yxatda yo'q turlar — qaror yoki pul bilan bog'liq (chegirma, xarajat, o'tkazma, qurilma, kassa topshirish,
# qaytmagan libos, obuna) — o'chirilmaydi: ular javobsiz qolsa ish to'xtaydi.
_R, _S, _K = Xodim.Rol.RAHBAR, Xodim.Rol.SOTUVCHI, Xodim.Rol.KASSIR
XABAR_GURUHLARI = {
    'zakaz': ("Yangi zakaz va zakaz o'zgarishi", {'yangi_zakaz', 'zakaz_ozgardi'}, (_R, _S, _K)),
    'eslatma': ("Kunlik eslatmalar (kimga qo'ng'iroq qilish)", {'eslatma', 'primerka_yaqin'}, (_R, _S, _K)),
    'kunlik': ('Kunlik hisobot', {'kunlik_hisobot'}, (_R,)),
    'haftalik': ('Haftalik xulosa (dushanba)', {'haftalik_xulosa'}, (_R,)),
    'kassa': ('Kassa farqlari va tuzatishlar', {'kassa_farqi', 'seyf_farqi', 'terminal_farqi', 'kassa_topshirish_farqi',
                                               'tolov_tuzatildi'}, (_R,)),
    'libos': ('Yangi libos va sanoq', {'yangi_libos', 'libos_sanogi'}, (_R,)),
}
_TUR_GURUHI = {tur: kalit for kalit, (_, turlar, _) in XABAR_GURUHLARI.items() for tur in turlar}


def xabar_ochirilganmi(xodim, tur):
    return _TUR_GURUHI.get(tur) in (xodim.bot_ochirilgan or [])


# Muhim xabarlar toifalari: xodim tinch vaqtda ham kelsinmi yoki ertalabgacha kutsinmi — o'zi tanlaydi.
# Hech bir ro'yxatda yo'q turlar (yangi qurilma, PIN bloklanishi va h.k.) — xavfsizlik: doim darhol ketadi.
MUHIM_TOIFALAR = {
    'qaror': ("Qaror so'rovlari va javoblari", {
        'chegirma_sorovi', 'xarajat_tasdiq', 'xarajat_rad', 'otkazma_tasdiq', 'otkazma_keldi', 'otkazma_kelmadi',
        'kassa_topshirish', 'kassa_topshirish_kutilmoqda', 'kassa_topshirish_qabul'}, (_R, _S, _K)),
    'nazorat': ('Qaytmagan libos, zalog va kassa ogohlantirishlari', {
        'libos_qaytmadi', 'manfiy_hisob', 'zalog_tekshirilmadi', 'zalog_yoq'}, (_R, _S, _K)),
    'obuna': ("Obuna muddati va to'lovi", {'obuna_muddati', 'obuna_tolovi'}, (_R,)),
}
_TUR_TOIFASI = {tur: kalit for kalit, (_, turlar, _) in MUHIM_TOIFALAR.items() for tur in turlar}
# Jamlanmaga yig'iladigan guruhlar. Hisobot va eslatmalar yig'ilmaydi: ularning o'z vaqti bor.
JAMLANADIGAN = {'zakaz', 'kassa', 'libos'}
JAMLANMA_SOATLARI = (9, 13, 18, 20)
TINCH_VAQTLAR = ((22, 8), (21, 9), (23, 7))
ESLATMA_SOATLARI = (8, 9, 10, 12)
ESLATMA_SOATI = 9  # tanlanmagan bo'lsa
JAMLANMA_MAKS = 3500  # bitta Telegram xabari 4096 belgidan oshmasin


def bot_soz(xodim):
    """Xodimning botdagi sozlamalari — buzuq yoki eskirgan qiymatlar standartga qaytarilgan holda."""
    s = xodim.bot_sozlama if isinstance(xodim.bot_sozlama, dict) else {}
    tinch = tuple(s.get('tinch') or ())
    return {'jamlanma': s.get('jamlanma') if s.get('jamlanma') in JAMLANMA_SOATLARI else None,
            'eslatma': s.get('eslatma') if s.get('eslatma') in ESLATMA_SOATLARI else ESLATMA_SOATI,
            'primerka': bool(s.get('primerka')),
            'tinch': tinch if tinch in TINCH_VAQTLAR else None,
            'tinch_kutadi': [k for k in (s.get('tinch_kutadi') or []) if k in MUHIM_TOIFALAR],
            'maxfiy': bool(s.get('maxfiy'))}


def _keyingi_soat(hozir, soat):
    t = hozir.replace(hour=soat, minute=0, second=0, microsecond=0)
    return t if t > hozir else t + timedelta(days=1)


def yuborish_vaqti(xodim, tur, hozir=None):
    """Xabar qachon ketadi: `None` — darhol; aks holda shu vaqtgacha navbatda kutadi (jamlanma yoki tinch vaqt)."""
    s = bot_soz(xodim)
    hozir = hozir or timezone.localtime()
    guruh = _TUR_GURUHI.get(tur)
    if guruh in JAMLANADIGAN and s['jamlanma'] is not None:
        return _keyingi_soat(hozir, s['jamlanma'])
    if s['tinch']:
        bosh, oxir = s['tinch']
        if (hozir.hour >= bosh or hozir.hour < oxir) and (guruh or _TUR_TOIFASI.get(tur) in s['tinch_kutadi']):
            return _keyingi_soat(hozir, oxir)
    return None


YUBORISH_PAUZASI = 0.05  # ketma-ket yuborishlar orasidagi pauza: bitta botning limiti butun platformaga umumiy


def som(n):
    return f'{n:,}'.replace(',', ' ') + " so'm"


# ---------- yuborish ----------

def _yubor(xabar_id):
    """Bitta xabarni yuboradi. Telegram limit bersa (429) xabar navbatda qoladi va `False` qaytadi."""
    xabar = Xabar.objects.select_related('xodim__salon').filter(id=xabar_id, holat=Xabar.Holat.KUTILMOQDA).first()
    if not xabar or (xabar.keyin and xabar.keyin > timezone.now()):
        return None
    matn, tugmalar = xabar.matn, xabar.tugmalar
    if bot_soz(xabar.xodim)['maxfiy']:  # chatda mazmun ko'rinmaydi — xodim tugmani bosgandagina ochiladi
        matn = f"🔔 {xabar.xodim.salon.nomi}: yangi xabar"
        tugmalar = [[{'text': "👁 Ko'rsatish", 'callback_data': f'k:{xabar.id}'}]]
    try:
        telegram.xabar_yubor(xabar.xodim.telegram_id, matn, tugmalar,
                             **({'jim': True} if xabar.tur in JIM_TURLAR else {}))
        xabar.holat, xabar.yuborilgan = Xabar.Holat.YUBORILDI, timezone.now()
    except telegram.TelegramLimitXatosi:
        # Vaqtinchalik: XATO deb belgilansa xabar butunlay yo'qolar edi (XATO qayta yuborilmaydi).
        return False
    except telegram.TelegramXatosi as e:
        xabar.holat, xabar.xato_matni = Xabar.Holat.XATO, str(e)[:300]
    except Exception:  # noqa: BLE001 — xabarnoma asosiy amalni hech qachon yiqitmasligi kerak
        log.exception('Telegram xabarini yuborishda kutilmagan xato')
        xabar.holat, xabar.xato_matni = Xabar.Holat.XATO, 'kutilmagan xato'
    xabar.save(update_fields=['holat', 'yuborilgan', 'xato_matni'])
    return True


def xabar_yoz(xodim, tur, matn, tugmalar=None, kalit='', darhol=True):
    """Xodimga xabar yozadi va (bot sozlangan, xodim ulangan bo'lsa) tranzaksiya tugagach yuboradi.

    `kalit` berilsa, shu xodimga shu kalitli xabar bir marta yoziladi (takroriy eslatmalarga qarshi).
    `darhol=False` — faqat navbatga: bot jarayoni keyingi aylanishda yuboradi (so'rov Telegramni kutmaydi).
    """
    if xabar_ochirilganmi(xodim, tur):
        return None  # xodim bu guruhni botda o'zi o'chirgan — yozilmaydi ham (qayta yoqsa keyingisi keladi)
    keyin = None
    if not xodim.telegram_id:
        holat = Xabar.Holat.ULANMAGAN
    else:
        holat = Xabar.Holat.KUTILMOQDA
        keyin = yuborish_vaqti(xodim, tur)
    try:
        with transaction.atomic():
            xabar = Xabar.objects.create(salon_id=xodim.salon_id, xodim=xodim, tur=tur, matn=matn, tugmalar=tugmalar,
                                         kalit=kalit, holat=holat, keyin=keyin)
    except IntegrityError:
        return None  # shu kalit bilan allaqachon yozilgan
    if darhol and not keyin and holat == Xabar.Holat.KUTILMOQDA and telegram.sozlangan(xodim.salon_id):
        transaction.on_commit(lambda: _yubor(xabar.id))
    return xabar


def rahbarlarga(salon, tur, matn, tugmalar=None, kalit='', darhol=True):
    """Salonning barcha faol rahbarlariga (FT-11.2, FT-12.10, FT-17.5, FT-1.7)."""
    try:
        return [xabar_yoz(x, tur, matn, tugmalar, kalit, darhol)
                for x in Xodim.objects.filter(salon=salon, rol=Xodim.Rol.RAHBAR, faol=True)]
    except Exception:  # noqa: BLE001
        log.exception('Rahbarlarga xabar yozib bo\'lmadi')
        return []


def kutayotganlarni_yubor():
    """Yuborilmay qolgan xabarlarni qayta yuboradi (bot keyinroq sozlangan yoki tarmoq uzilgan bo'lsa).

    Bitta bot butun platformaga xizmat qiladi, shu sababli yuborishlar orasida kichik pauza qo'yiladi va
    Telegram limit bersa (429) to'xtatiladi — qolganlari keyingi aylanishda ketadi.
    """
    if not telegram.barcha_tokenlar():
        return 0
    hozir = timezone.now()
    kecha = hozir - timedelta(days=1)
    navbat = (Xabar.objects.filter(holat=Xabar.Holat.KUTILMOQDA).filter(Q(yaratilgan__gt=kecha) | Q(keyin__gt=kecha))
              .exclude(keyin__gt=hozir))
    _jamla(navbat, hozir)
    qatorlar = list(navbat.values_list('id', flat=True))
    soni = 0
    for i in qatorlar:
        if _yubor(i) is False:  # limit — to'xtaymiz (davom etsak, navbat yana 429 bo'lardi)
            break
        soni += 1
        time.sleep(YUBORISH_PAUZASI)
    return soni


def _jamla(navbat, hozir):
    """Kutib turgan (tinch vaqt yoki jamlanma) tugmasiz xabarlar har xodimga bitta xabar bo'lib ketadi.

    Tugmali xabarlar (qaror so'rovi, «Bog'landim») birlashtirilmaydi — tugmasi yo'qolmasin.
    """
    guruhlar = {}
    for x in navbat.filter(keyin__isnull=False).exclude(tur='jamlanma').order_by('id'):
        if not x.tugmalar:
            guruhlar.setdefault(x.xodim_id, []).append(x)
    for xodim_id, xabarlar in guruhlar.items():
        if len(xabarlar) < 2:
            continue
        bolaklar, joriy = [], ''
        for x in xabarlar:
            if joriy and len(joriy) + len(x.matn) > JAMLANMA_MAKS:
                bolaklar.append(joriy)
                joriy = ''
            joriy += ('\n\n' if joriy else '') + x.matn[:JAMLANMA_MAKS]
        bolaklar.append(joriy)
        with transaction.atomic():
            for i, bolak in enumerate(bolaklar):
                Xabar.objects.create(salon_id=xabarlar[0].salon_id, xodim_id=xodim_id, tur='jamlanma', keyin=hozir,
                                     matn=(f"🗞 Jamlanma · {len(xabarlar)} ta xabar\n\n" if not i else '') + bolak)
            Xabar.objects.filter(id__in=[x.id for x in xabarlar]).update(
                holat=Xabar.Holat.YUBORILDI, yuborilgan=hozir, xato_matni='jamlanmada')


def korsat_tugma_ishla(chat_id, xabar_id):
    """`k:<xabar_id>` — maxfiy rejimda yashirib yuborilgan xabarni ochadi: (qisqa javob, matn, tugmalar)."""
    x = Xabar.objects.select_related('xodim').filter(id=xabar_id, xodim__telegram_id=chat_id, xodim__faol=True).first()
    if not x:
        return "Xabar topilmadi.", None, None
    return '', x.matn, x.tugmalar


# ---------- xodimni botga ulash ----------

def ulash_kodi_yarat(xodim):
    TelegramUlash.objects.filter(xodim=xodim).delete()
    return TelegramUlash.objects.create(salon_id=xodim.salon_id, xodim=xodim, kod=secrets.token_hex(4),
                                        tugaydi=timezone.now() + ULASH_MUDDATI)


def start_ishla(chat_id, kod):
    """`/start <kod>`: kod to'g'ri va muddati o'tmagan bo'lsa, shu Telegram akkaunti xodimga bog'lanadi.

    Bot bitta bo'lgani uchun bitta Telegram akkaunti bir nechta salonning xodimi bo'lishi mumkin —
    shu sababli boshqa salonlardagi mavjud bog'lanishlar uzilmaydi.
    """
    u = TelegramUlash.objects.select_related('xodim').filter(kod=(kod or '').strip(), tugaydi__gt=timezone.now()).first()
    if not u:
        return "Kod noto'g'ri yoki muddati o'tgan. Ilovada «Telegramni ulash» tugmasini qayta bosing."
    # Bitta akkaunt shu salonning ikkinchi xodimida qolmasin (bir chat — bir xodim), lekin boshqa
    # salonlardagi bog'lanishlarga tegmaymiz: bitta platforma boti hammaga xizmat qiladi.
    Xodim.objects.filter(salon_id=u.salon_id, telegram_id=chat_id).exclude(id=u.xodim_id).update(telegram_id=None)
    Xodim.objects.filter(id=u.xodim_id).update(telegram_id=chat_id)
    u.delete()
    return f"{u.xodim.ism}, Telegram ulandi. Endi Libosa xabarlari shu yerga keladi."


def uzish(xodim):
    Xodim.objects.filter(id=xodim.id).update(telegram_id=None)
    TelegramUlash.objects.filter(xodim=xodim).delete()


# ---------- platforma egasini botga ulash va ariza xabari (FT-4.14) ----------

def platforma_ulash_kodi():
    """Platforma egasini botga ulash uchun bir martalik kod yaratadi (15 daqiqa amal qiladi)."""
    s = platforma_sozlama()
    s.telegram_ulash_kod = secrets.token_hex(4)
    s.telegram_ulash_tugaydi = timezone.now() + ULASH_MUDDATI
    s.save(update_fields=['telegram_ulash_kod', 'telegram_ulash_tugaydi'])
    return s.telegram_ulash_kod


def start_ishla_platforma(chat_id, kod):
    """Platforma egasining `/start <kod>`: kod mos kelsa egasining Telegram chatini bog'laydi.

    Kod platforma kodiga mos kelmasa (yoki muddati o'tgan bo'lsa) `None` qaytaradi — chaqiruvchi
    xodim ulashiga (`start_ishla`) tushadi.
    """
    s = platforma_sozlama()
    if not s.telegram_ulash_kod or not s.telegram_ulash_tugaydi:
        return None
    if (kod or '').strip() != s.telegram_ulash_kod or s.telegram_ulash_tugaydi < timezone.now():
        return None
    s.telegram_chat_id = chat_id
    s.telegram_ulash_kod = ''
    s.telegram_ulash_tugaydi = None
    s.save(update_fields=['telegram_chat_id', 'telegram_ulash_kod', 'telegram_ulash_tugaydi'])
    return "Platforma egasi ulandi. Endi a'zo bo'lish so'rovlari shu yerga keladi."


def platforma_arizasi(a):
    """Platforma egasiga yangi so'rov («a'zo bo'lish» / «bog'lanish») haqida Telegram xabar yuboradi.

    Bot sozlanmagan yoki ega ulangan bo'lmasa jim o'tadi — so'rov panelda baribir ko'rinadi.
    Yuborishdagi xato ham asosiy amalni buzmaydi (so'rov allaqachon saqlangan).
    """
    try:
        s = platforma_sozlama()
        if not s.telegram_chat_id or not telegram.sozlangan():
            return
        tur = dict(Ariza.Tur.choices).get(a.tur, a.tur)
        qatorlar = [f"Yangi so'rov: {tur}", f"👤 {a.ism}"]
        if a.telefon:
            qatorlar.append(f"📞 {a.telefon}")
        if a.salon_nomi:
            qatorlar.append(f"🏢 {a.salon_nomi}")
        if a.xabar:
            qatorlar.append(f"💬 {a.xabar}")
        telegram.xabar_yubor(s.telegram_chat_id, '\n'.join(qatorlar),
                             [[{'text': "✅ Bog'landim", 'callback_data': f'ar:{a.id}'}]])
    except Exception:  # noqa: BLE001 — xabarnoma so'rovni hech qachon buzmasin
        log.exception("Platforma egasiga ariza xabarini yuborib bo'lmadi")


# ---------- chegirma so'rovi tugmalari ----------

def chegirma_matni_va_tugmalari(sorov):
    z = sorov.zakaz
    miqdor = f'{float(sorov.foiz):g}%' if sorov.foiz is not None else som(sorov.summa)
    matn = (f"Chegirma so'rovi\nZakaz #{z.raqam}, jami {som(z.jami)}\n"
            f"{sorov.sotuvchi.ism if sorov.sotuvchi else 'Sotuvchi'} {miqdor} chegirma so'radi.\n"
            f"Sabab: {sorov.get_sabab_display()}{'. ' + sorov.izoh if sorov.izoh else ''}")
    tugmalar = [[{'text': 'Tasdiqlash', 'callback_data': f'ch:{sorov.id}:t'},
                 {'text': 'Rad etish', 'callback_data': f'ch:{sorov.id}:r'}]]
    return matn, tugmalar


def chegirma_sorovi_xabari(sorov):
    """Rahbarga «Tasdiqlash / Rad etish» tugmalari bilan so'rov (FT-11.2)."""
    matn, tugmalar = chegirma_matni_va_tugmalari(sorov)
    return rahbarlarga(sorov.zakaz.salon, 'chegirma_sorovi', matn, tugmalar)


def yangi_zakaz_xabari(zakaz):
    """Yangi zakaz — uni olgan xodimga va rahbarlarga, ovozsiz (foydalanuvchi qarori, 2026-11-11).

    Maqsad — arxiv: ilova ochilmay qolsa ham (internet, server) zakaz ma'lumoti Telegram chatida qoladi.
    """
    try:
        from .bot_menyu import zakaz_matni
        matn = zakaz_matni(zakaz, 'Yangi zakaz\n')
        kimga = {x.id: x for x in Xodim.objects.filter(salon_id=zakaz.salon_id, rol=Xodim.Rol.RAHBAR, faol=True)}
        if zakaz.sotuvchi_id and zakaz.sotuvchi.faol:
            kimga[zakaz.sotuvchi_id] = zakaz.sotuvchi
        return [xabar_yoz(x, 'yangi_zakaz', matn, kalit=f'yangi_zakaz:{zakaz.id}', darhol=False) for x in kimga.values()]
    except Exception:  # noqa: BLE001 — xabar zakazni hech qachon buzmasin
        log.exception('Yangi zakaz xabarini yozib bo\'lmadi')
        return []


def tugma_ishla(chat_id, data):
    """Inline tugma bosilishi. Bosgan akkaunt shu so'rov salonining faol rahbari bo'lishi shart.

    Bitta akkaunt bir nechta salonga bog'langan bo'lishi mumkin — shu sababli salon so'rovning o'zidan
    olinadi, akkauntdan emas.
    """
    from apps.orders.discounts import ChegirmaXatosi, chegirma_qarori
    from apps.orders.models import ChegirmaSorovi

    qismlar = (data or '').split(':')
    if len(qismlar) == 3 and qismlar[0] == 'qr' and qismlar[1].isdigit() and qismlar[2] in ('t', 'h', 'r'):
        return qurilma_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2])
    if len(qismlar) == 3 and qismlar[0] == 'kr' and qismlar[1].isdigit() and qismlar[2] in ('r', 'y'):
        return kirish_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2])
    if len(qismlar) == 3 and qismlar[0] == 'kt' and qismlar[1].isdigit() and qismlar[2] in ('q', 'b'):
        return kassa_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2])
    if len(qismlar) == 3 and qismlar[0] == 'ot' and qismlar[1].isdigit() and qismlar[2] in ('k', 'y'):
        return otkazma_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2] == 'k')
    if len(qismlar) == 3 and qismlar[0] == 'xr' and qismlar[1].isdigit() and qismlar[2] in ('t', 'r'):
        return xarajat_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2] == 't')
    if len(qismlar) == 2 and qismlar[0] == 'pb' and qismlar[1].isdigit():
        return pin_blok_tugma_ishla(chat_id, int(qismlar[1]))
    if len(qismlar) == 3 and qismlar[0] == 'bg' and qismlar[1].isdigit():
        return boglandim_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2])
    if len(qismlar) == 2 and qismlar[0] == 'ar' and qismlar[1].isdigit():
        return ariza_tugma_ishla(chat_id, int(qismlar[1]))
    if len(qismlar) == 3 and qismlar[0] == 'ob' and qismlar[1].isdigit() and qismlar[2] in ('1', '3', 'r'):
        return obuna_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2])
    if len(qismlar) == 2 and qismlar[0] == 'tl' and qismlar[1].isdigit():
        return toladim_tugma_ishla(chat_id, int(qismlar[1]))
    if len(qismlar) != 3 or qismlar[0] != 'ch' or not qismlar[1].isdigit() or qismlar[2] not in ('t', 'r'):
        return "Noma'lum buyruq."
    sorov = ChegirmaSorovi.objects.filter(id=int(qismlar[1])).first()
    if not sorov:
        return "So'rov topilmadi."
    xodim = _salon_rahbari(sorov.salon_id, chat_id)
    if not xodim:
        return "Bu amal faqat shu salon rahbariga ruxsat etilgan."
    try:
        s = chegirma_qarori(salon=xodim.salon, rahbar=xodim, sorov=sorov, tasdiqlash=qismlar[2] == 't')
    except ChegirmaXatosi as e:
        return str(e)
    if s.holat == ChegirmaSorovi.Holat.TASDIQLANDI:
        return f"Tasdiqlandi: chegirma {som(s.tasdiqlangan_summa)}. Zakaz #{s.zakaz.raqam}, yangi jami {som(s.zakaz.jami)}."
    return f"Rad etildi. Zakaz #{s.zakaz.raqam} chegirmasiz narxda davom etadi."


# ---------- xarajat, PIN blok, «Bog'landim», ariza tugmalari ----------

def xarajat_tugma_ishla(chat_id, xid, tasdiqlash):
    """«Tasdiqlash / Rad etish»: sotuvchi kiritgan xarajat bo'yicha rahbar qarori."""
    from apps.finance.models import Xarajat
    from apps.finance.services import XarajatXatosi, xarajat_qarori

    x = Xarajat.objects.filter(id=xid).first()
    if not x:
        return 'Xarajat topilmadi.'
    rahbar = _salon_rahbari(x.salon_id, chat_id)
    if not rahbar:
        return 'Bu amal faqat shu salon rahbariga ruxsat etilgan.'
    if not salon_yoza_oladimi(rahbar.salon):
        return "Salon «faqat ko'rish» holatida."
    try:
        x = xarajat_qarori(salon=rahbar.salon, rahbar=rahbar, xarajat=x, tasdiqlash=tasdiqlash)
    except XarajatXatosi as e:
        return str(e)
    return f'Tasdiqlandi: {som(x.summa)}.' if tasdiqlash else f'Rad etildi: {som(x.summa)}.'


def pin_blok_tugma_ishla(chat_id, xodim_id):
    """«Blokdan chiqarish»: PIN xato kiritilib bloklangan xodimni rahbar kutmasdan ochadi."""
    x = Xodim.objects.filter(id=xodim_id).first()
    if not x:
        return 'Xodim topilmadi.'
    rahbar = _salon_rahbari(x.salon_id, chat_id)
    if not rahbar:
        return 'Bu amal faqat shu salon rahbariga ruxsat etilgan.'
    if not x.bloklangan:
        return f'{x.ism} bloklanmagan (muddat o\'tgan yoki allaqachon ochilgan).'
    Xodim.objects.filter(id=x.id).update(bloklangan_gacha=None, xato_urinish=0)
    jurnalga_yoz(rahbar.salon, rahbar, 'pin_blok_ochildi', f'xodim {x.ism} (Telegram)')
    return f'{x.ism} blokdan chiqarildi.'


def boglandim_tugma_ishla(chat_id, zakaz_id, tur):
    """Eslatma ostidagi «Bog'landim» (FT-14.2): ilovadagi tugma bilan bir xil yozuv — eslatma hammada yopiladi."""
    from apps.orders.models import Zakaz, ZakazTarixi

    z = Zakaz.objects.select_related('salon').filter(id=zakaz_id).first()
    x = z and Xodim.objects.filter(salon_id=z.salon_id, telegram_id=chat_id, faol=True).first()
    if not x:
        return 'Zakaz topilmadi.'
    if not salon_yoza_oladimi(z.salon):
        return "Salon «faqat ko'rish» holatida."
    if ZakazTarixi.objects.filter(zakaz=z, harakat='boglandi', eski=tur[:30], vaqt__date=timezone.localdate()).exists():
        return 'Allaqachon belgilangan.'
    ZakazTarixi.objects.create(salon=z.salon, zakaz=z, xodim=x, harakat='boglandi', eski=tur[:30],
                               yangi="Mijoz bilan bog'lanildi (Telegram)")
    return f"Belgilandi: {x.ism} bog'landi."


def ariza_tugma_ishla(chat_id, ariza_id):
    """Platforma egasi so'rov egasi bilan bog'langanini belgilaydi (panelda «ko'rilgan» bo'ladi)."""
    if platforma_sozlama().telegram_chat_id != chat_id:
        return 'Bu amal faqat platforma egasiga ruxsat etilgan.'
    if not Ariza.objects.filter(id=ariza_id).update(korilgan=True):
        return "So'rov topilmadi."
    return "Bog'lanildi deb belgilandi."


# ---------- kassa: topshirilgan naqdni qabul qilish ----------

def kassa_tugma_ishla(chat_id, tid, amal):
    """«✅ Qabul qildim» — topshiruvchi aytgan summa qabul qilinadi; «✏️ Boshqa summa» — summa ilovada kiritiladi.
    Tugmani faqat pul topshirilgan xodimning o'zi bosa oladi."""
    from apps.cash.models import KassaTopshirish
    from apps.cash.services import KassaXatosi, topshiriqni_qabul

    t = KassaTopshirish.objects.select_related('kimga', 'salon').filter(id=tid).first()
    if not t or t.kimga.telegram_id != chat_id or not t.kimga.faol:
        return 'Bu pul sizga topshirilmagan.'
    if t.holat == KassaTopshirish.Holat.QABUL:
        return 'Allaqachon qabul qilingan.'
    if amal == 'b':
        return "Sanagan summangizni ilovada kiriting: Kassa → «Sizga topshirilgan pul» → «Boshqa summa»."
    try:
        t = topshiriqni_qabul(salon=t.salon, xodim=t.kimga, topshirish=t)
    except KassaXatosi as e:
        return str(e)
    return f'Qabul qilindi: {som(t.qabul_summa)}.'


def otkazma_tugma_ishla(chat_id, tid, keldi):
    """«✅ Keldi / ❌ Kelmadi»: o'tkazma, Click yoki Payme to'lovi rahbar hisobiga tushdimi."""
    from apps.cash.models import Tolov
    from apps.cash.services import KassaXatosi, otkazma_tasdiqlash

    t = Tolov.objects.filter(id=tid).first()
    if not t:
        return "To'lov topilmadi."
    xodim = _salon_rahbari(t.salon_id, chat_id)
    if not xodim:
        return 'Bu amal faqat shu salon rahbariga ruxsat etilgan.'
    try:
        t = otkazma_tasdiqlash(salon=xodim.salon, rahbar=xodim, tolov=t, keldi=keldi)
    except KassaXatosi as e:
        return str(e)
    return 'Keldi — tasdiqlandi.' if keldi else "Kelmadi — to'lov hisobdan chiqarildi, xodimga xabar berildi."


# ---------- yangi qurilmani Telegram orqali tasdiqlash (FT-22.2) ----------

QURILMA_TOKEN_MUDDATI = timedelta(minutes=10)
QURILMA_TOKEN_ZAXIRA = timedelta(minutes=2)    # shundan kam qolgan havola qayta ko'rsatilmaydi — yangisi beriladi
QURILMA_KIRISH_OYNASI = timedelta(minutes=15)  # Telegramdan tasdiqlagan rahbar shu vaqt ichida ikkinchi kodsiz kiradi
QURILMA_XABAR_CHEGARASI = 3                    # 10 daqiqada salon rahbarlariga ketadigan «yangi qurilma» xabarlari


def _xesh(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _qurilma_tokeni(q):
    """Token qurilma va muddatdan HMAC bilan hisoblanadi: bazada faqat xeshi turadi, lekin muddat tugamaguncha
    xuddi shu havolani qayta ko'rsatish mumkin (ikki tab, sahifa yangilanishi eski QR ni buzmaydi)."""
    imzo = hmac.new(settings.SECRET_KEY.encode(), f'qurilma:{q.id}:{q.tg_token_tugaydi.timestamp()}'.encode(),
                    hashlib.sha256).digest()
    return base64.urlsafe_b64encode(imzo[:24]).decode().rstrip('=')


def qurilma_tasdiq_havolasi(qurilma):
    """Kutayotgan qurilma uchun `(t.me/<bot>?start=q_<token>, tugaydi)` yoki `(None, None)`.

    Bot sozlanmagan yoki salonda Telegram ulagan rahbar bo'lmasa havola yo'q (u hech kimga ishlamasdi).
    Amaldagi havola muddati tugaguncha o'sha qoladi; faqat tugashiga oz qolganda yangisi chiqariladi.
    """
    nomi = (telegram.bot_nomi() or '').lstrip('@')
    if not nomi or not telegram.sozlangan() or not Xodim.objects.filter(
            salon_id=qurilma.salon_id, rol=Xodim.Rol.RAHBAR, faol=True, telegram_id__isnull=False).exists():
        return None, None
    if not qurilma.tg_token_tugaydi or qurilma.tg_token_tugaydi < timezone.now() + QURILMA_TOKEN_ZAXIRA:
        qurilma.tg_token_tugaydi = timezone.now() + QURILMA_TOKEN_MUDDATI
        qurilma.tg_token = _xesh(_qurilma_tokeni(qurilma))
        qurilma.save(update_fields=['tg_token', 'tg_token_tugaydi'])
    return f'https://t.me/{nomi}?start=q_{_qurilma_tokeni(qurilma)}', qurilma.tg_token_tugaydi


def _qurilma_tavsifi(q):
    return f"«{q.nomi}»" + (f"\n📱 {q.modeli}" if q.modeli else '')


def _tolov_xabari(x, nima):
    """Egaga: qaysi salon, kim, obuna holati, tarif, telefon — «to'ladim» va chek uchun bir xil."""
    from .bot_menyu import obuna_holati_matni
    s = x.salon
    qatorlar = [f"💳 {s.nomi}: rahbar {x.ism} {nima}.", obuna_holati_matni(s)]
    if s.tarif_id:
        qatorlar.append(f'Tarif: {s.tarif.nomi}' + (f' — oyiga {som(s.tarif.oylik_narx)}' if s.tarif.oylik_narx else ''))
    if s.rahbar_telefon:
        qatorlar.append(f'Tel: {s.rahbar_telefon}')
    qatorlar.append("Pul kelganini tekshirib, pastdagi tugma bilan qaror qiling.")
    return '\n'.join(qatorlar)


def obuna_tugmalari(tolov):
    """Egaga: so'rov ostidagi qaror tugmalari — bir bosishda tarixga yoziladi va obuna uzayadi."""
    narx = tolov.salon.tarif.oylik_narx if tolov.salon.tarif_id else 0
    return [[{'text': f'✅ {oy} oy' + (f' — {som(narx * oy)}' if narx else ''), 'callback_data': f'ob:{tolov.id}:{oy}'}]
            for oy in (1, 3)] + [[{'text': '❌ Rad etish', 'callback_data': f'ob:{tolov.id}:r'}]]


def obuna_tugma_ishla(chat_id, tolov_id, qaror):
    """`ob:<id>:<1|3|r>` — platforma egasining to'lov so'rovi bo'yicha qarori."""
    from apps.tenants import obuna
    from apps.tenants.models import ObunaTolovi
    if platforma_sozlama().telegram_chat_id != chat_id:
        return "Bu amal faqat platforma egasiga ruxsat etilgan."
    t = ObunaTolovi.objects.filter(id=tolov_id).first()
    if not t:
        return "To'lov so'rovi topilmadi."
    try:
        if qaror == 'r':
            obuna.tolov_rad(t.id, 'bot')
            return "Rad etildi. Rahbarga xabar berildi."
        t = obuna.tolov_qabul(t.salon_id, int(qaror), 'bot', tolov_id=t.id, manba=ObunaTolovi.Manba.BOT)
    except obuna.ObunaXatosi as e:
        return str(e)
    return (f"Qabul qilindi: {t.oylar} oy" + (f', {som(t.summa)}' if t.summa else '') + f". Obuna {t.yangi_obuna:%d.%m.%Y} gacha. "
            + ("Rahbarga xabar berildi." if t.summa else "Tarifda narx yo'q — summani panelda kiriting."))


def chek_egaga(x, tur, fayl_id, izoh=''):
    """Rahbar yuborgan chekni (Telegramdagi fayl — `file_id`) egaga qaror tugmalari bilan uzatadi.

    Fayl serverga yuklab olinmaydi; so'rov tarixga «kutilmoqda» bo'lib yoziladi (apps/tenants/obuna.py).
    """
    from apps.tenants import obuna

    from .egaga import ega_manzili
    manzil = ega_manzili()
    if not manzil or not fayl_id:
        return False
    t = obuna.tolov_sorovi(x.salon, x, fayl_id, tur, izoh)
    matn = _tolov_xabari(x, "obuna to'lovi chekini yubordi") + (f'\nIzoh: {izoh[:200]}' if izoh else '')
    try:
        telegram.api('sendPhoto' if tur == 'photo' else 'sendDocument', _token=manzil[1], chat_id=manzil[0],
                     caption=matn[:1000], reply_markup={'inline_keyboard': obuna_tugmalari(t)}, **{tur: fayl_id})
        return True
    except telegram.TelegramXatosi:
        return False


def toladim_tugma_ishla(chat_id, xodim_id):
    """Rahbar obuna uchun to'laganini bildirdi → platforma egasiga xabar (salonga kuniga bir marta).

    Obuna o'zi uzaymaydi: pul kelganini ega tekshiradi va platforma panelida uzaytiradi.
    """
    from django.core.cache import cache

    from apps.tenants import obuna

    from .egaga import ega_manzili
    x = Xodim.objects.filter(id=xodim_id, telegram_id=chat_id, faol=True, rol=Xodim.Rol.RAHBAR).select_related('salon__tarif').first()
    if not x:
        return "Bu amal faqat salon rahbariga ruxsat etilgan."
    s = x.salon
    kalit = f'toladim:{s.id}:{timezone.localdate()}'
    if cache.get(kalit):
        return "Bugun platforma egasiga xabar berilgan. To'lov tekshirilgach obuna uzaytiriladi."
    manzil = ega_manzili()
    if not manzil:
        return "Platforma egasiga xabar yetmadi. Birozdan keyin qayta urinib ko'ring."
    t = obuna.tolov_sorovi(s, x)
    try:
        telegram.xabar_yubor(manzil[0], _tolov_xabari(x, "obuna uchun to'lov qilganini bildirdi (cheksiz)"),
                             obuna_tugmalari(t), token=manzil[1])
    except telegram.TelegramXatosi:
        return "Platforma egasiga xabar yetmadi. Birozdan keyin qayta urinib ko'ring."
    cache.set(kalit, 1, 24 * 3600)
    return "Platforma egasiga xabar berildi. To'lov tekshirilgach obuna uzaytiriladi."


def _salon_rahbari(salon_id, chat_id):
    """Telegram akkaunti shu salonning faol rahbarimi. Salon har doim so'rov/qurilmaning o'zidan olinadi."""
    return Xodim.objects.filter(salon_id=salon_id, telegram_id=chat_id, faol=True, rol=Xodim.Rol.RAHBAR).first()


def qurilma_kutmoqda_xabari(qurilma):
    """Yangi qurilma ruxsat kutayotgani haqida rahbarlarga «Ruxsat / Rad» tugmali xabar.

    Navbatga yoziladi va bot jarayoni yuboradi — salon logini Telegramni kutib qolmaydi. Parolni bilgan kishi
    loginni qayta-qayta bosib rahbarlarni xabarga ko'mib tashlamasligi uchun 10 daqiqada ko'pi bilan 3 ta.
    """
    if Xabar.objects.filter(salon_id=qurilma.salon_id, tur='qurilma_kutmoqda',
                            yaratilgan__gt=timezone.now() - timedelta(minutes=10)).values('kalit').distinct().count() \
            >= QURILMA_XABAR_CHEGARASI:
        return []
    tugmalar = [[{'text': '✅ Ruxsat', 'callback_data': f'qr:{qurilma.id}:t'},
                 {'text': '❌ Rad', 'callback_data': f'qr:{qurilma.id}:r'}]]
    return rahbarlarga(qurilma.salon, 'qurilma_kutmoqda',
                       f"Yangi qurilma ruxsat so'ramoqda:\n{_qurilma_tavsifi(qurilma)}", tugmalar,
                       kalit=f'qurilma:{qurilma.id}', darhol=False)


QURILMA_FAQAT_KORISH = "Salon «faqat ko'rish» holatida: qurilmalarni o'zgartirib bo'lmaydi."


def qurilma_tasdiqla(q, rahbar, manba='', kodsiz=False):
    """Qurilmani ishonchli qiladi. `manba` jurnalga yoziladi (Telegram havola/tugma, qurilmada PIN yoki ilova).

    `kodsiz` — rahbar shaxsini Telegram havolasi orqali tasdiqlagan: shu qurilmadagi keyingi kirishida
    ikkinchi kod so'ralmaydi (`tg_tasdiq_kodsiz_kirish`).
    """
    q.tasdiqlangan, q.tasdiqlagan, q.tg_token, q.tg_token_tugaydi = True, rahbar, '', None
    q.tg_tasdiqlangan = timezone.now() if kodsiz else None
    q.save(update_fields=['tasdiqlangan', 'tasdiqlagan', 'tg_token', 'tg_token_tugaydi', 'tg_tasdiqlangan'])
    jurnalga_yoz(q.salon, rahbar, 'qurilma_tasdiqlandi', f'qurilma {q.nomi}' + (f' ({manba})' if manba else ''))


OXIRGI_QURILMA = "Oxirgi ishonchli qurilmani chiqarib bo'lmaydi: hech kim kira olmay qoladi."


def qurilma_chiqar(q, rahbar, manba=''):
    """Qurilmani ro'yxatdan chiqaradi (sessiyalari ham yopiladi). Xato bo'lsa matnini, aks holda `None` qaytaradi.

    Salon qatori qulflanadi: ikki rahbar bir vaqtda ikki xil qurilmani chiqarsa, ikkalasi ham «boshqasi bor» deb
    o'tib, salonni ishonchli qurilmasiz qoldirib qo'ymasin.
    """
    with transaction.atomic():
        Salon.objects.select_for_update().filter(id=q.salon_id).first()
        q = IshonchliQurilma.objects.filter(id=q.id, faol=True).first()
        if not q:
            return "Qurilma allaqachon ro'yxatdan chiqarilgan."
        if q.tasdiqlangan and not IshonchliQurilma.objects.filter(
                salon_id=q.salon_id, faol=True, tasdiqlangan=True).exclude(id=q.id).exists():
            return OXIRGI_QURILMA
        q.faol = False
        q.save(update_fields=['faol'])
        jurnalga_yoz(q.salon, rahbar, 'qurilma_chiqarildi', f'qurilma {q.nomi}' + (f' ({manba})' if manba else ''))
    return None


def qurilma_start_ishla(chat_id, token):
    """`/start q_<token>`: havolani bosgan akkaunt shu salonning faol rahbari bo'lsa — qurilma ma'lumoti va
    «Ha, bu men / Yo'q» tugmalari. Qurilma faqat tugma bosilganda tasdiqlanadi: havolani aldov bilan
    yuborishsa ham, rahbar avval qaysi qurilma ekanini ko'radi.
    """
    q = IshonchliQurilma.objects.select_related('salon').filter(
        tg_token=_xesh(token), tg_token_tugaydi__gt=timezone.now(), faol=True).first() if token else None
    if not q:
        return "Havola eskirgan yoki allaqachon ishlatilgan. Qurilmada «Telegram orqali tasdiqlash» ni qayta bosing.", None
    if not _salon_rahbari(q.salon_id, chat_id):
        return "Bu havola faqat shu salon rahbari uchun.", None
    if not salon_yoza_oladimi(q.salon):
        return QURILMA_FAQAT_KORISH, None
    if q.tasdiqlangan:
        return f"{_qurilma_tavsifi(q)} allaqachon ishonchli.", None
    return (f"Yangi qurilma kirmoqchi:\n{_qurilma_tavsifi(q)}\nSalon: {q.salon.nomi}\n\n"
            f"Bu qurilma hozir sizning qo'lingizdami? Aks holda «Yo'q» ni bosing.",
            [[{'text': '✅ Ha, bu men', 'callback_data': f'qr:{q.id}:h'},
              {'text': "❌ Yo'q", 'callback_data': f'qr:{q.id}:r'}]])


def qurilma_tugma_ishla(chat_id, qid, amal):
    """Tugmalar: `t` — ruxsat, `h` — havola orqali «ha, bu men» (shu kirishda ikkinchi kod so'ralmaydi),
    `r` — rad/chiqarish. Salon tugmani bosgan akkauntdan emas, qurilmaning o'zidan olinadi."""
    q = IshonchliQurilma.objects.select_related('salon').filter(id=qid).first()
    if not q:
        return "Qurilma topilmadi."
    rahbar = _salon_rahbari(q.salon_id, chat_id)
    if not rahbar:
        return "Bu amal faqat shu salon rahbariga ruxsat etilgan."
    if not q.faol:
        return "Qurilma allaqachon ro'yxatdan chiqarilgan."
    if not salon_yoza_oladimi(q.salon):
        return QURILMA_FAQAT_KORISH
    if amal in ('t', 'h'):
        if q.tasdiqlangan:
            return f"«{q.nomi}» allaqachon ishonchli."
        havola_amalda = bool(q.tg_token_tugaydi and q.tg_token_tugaydi > timezone.now())
        if amal == 'h' and not havola_amalda:
            return "Havola muddati o'tgan. Qurilmada «Telegram orqali tasdiqlash» ni qayta bosing."
        qurilma_tasdiqla(q, rahbar, 'Telegram havola' if amal == 'h' else 'Telegram tugma', kodsiz=amal == 'h')
        return f"Ruxsat berildi: «{q.nomi}»."
    xato = qurilma_chiqar(q, rahbar, 'Telegram')
    return xato or f"«{q.nomi}» rad etildi va ro'yxatdan chiqarildi."


def tg_tasdiq_kodsiz_kirish(xodim, qurilma):
    """Rahbar shu qurilmani hozirgina Telegram havolasi orqali o'zi tasdiqlagan bo'lsa — bir marta ikkinchi kodsiz."""
    return bool(qurilma.tg_tasdiqlangan and qurilma.tasdiqlagan_id == xodim.id
                and qurilma.tg_tasdiqlangan > timezone.now() - QURILMA_KIRISH_OYNASI
                and IshonchliQurilma.objects.filter(id=qurilma.id, tg_tasdiqlangan=qurilma.tg_tasdiqlangan)
                .update(tg_tasdiqlangan=None))


# ---------- rahbar kirishi uchun kod (FT-1.1, FT-22.3) ----------

def kirish_kodi_kerak(xodim):
    """Rahbar Telegram ulagan va bot sozlangan bo'lsa, PIN dan tashqari Telegram kod talab qilinadi."""
    return xodim.rol == Xodim.Rol.RAHBAR and bool(xodim.telegram_id) and telegram.sozlangan(xodim.salon_id)


def kirish_kodi_yubor(xodim, qurilma=None):
    """Telegramga kirish so'rovi: «Ruxsat berish» tugmasi (asosiy yo'l — terish shart emas) va zaxira sifatida kod."""
    kod = f'{secrets.randbelow(10 ** 6):06d}'
    k, _ = KirishKodi.objects.update_or_create(xodim=xodim, defaults={
        'kod': make_password(kod), 'tugaydi': timezone.now() + KIRISH_KODI_MUDDATI, 'urinish': 0,
        'qurilma': qurilma, 'tasdiqlandi': None})
    joy = f" «{qurilma.nomi}» qurilmasidan" if qurilma else ''
    matn = (f"🔐 Libosa:{joy} {xodim.ism} nomidan kirish so'raldi.\n"
            f"Siz bo'lsangiz — «Ruxsat berish»ni bosing, ilova o'zi kiradi.\n\n"
            f"Yoki ilovada kirish kodi: {kod}\n5 daqiqa amal qiladi. Hech kimga bermang.")
    tugmalar = [[{'text': '✅ Ruxsat berish', 'callback_data': f'kr:{k.id}:r'},
                 {'text': '❌ Bu men emas', 'callback_data': f'kr:{k.id}:y'}]]
    try:
        telegram.xabar_yubor(xodim.telegram_id, matn, tugmalar=tugmalar)
    except telegram.TelegramXatosi:
        return False
    return True


def kirish_tugma_ishla(chat_id, kid, amal):
    """«Ruxsat berish» / «Bu men emas». Faqat so'rov egasining o'z Telegrami bosishi mumkin."""
    k = KirishKodi.objects.select_related('xodim').filter(id=kid).first()
    if not k:
        return "So'rov topilmadi: kirish allaqachon bajarilgan yoki bekor qilingan."
    if k.xodim.telegram_id != chat_id:
        return "Bu so'rov sizga tegishli emas."
    if k.tugaydi < timezone.now():
        return "So'rov muddati o'tgan. Ilovada PIN kodni qayta kiriting."
    if amal == 'y':
        k.delete()
        return "Kirish rad etildi. Agar bu siz bo'lmasangiz, PIN kodingizni almashtiring."
    if not k.tasdiqlandi:
        k.tasdiqlandi = timezone.now()
        k.save(update_fields=['tasdiqlandi'])
    return "✅ Ruxsat berildi — ilova o'zi kiradi."


RAHBAR_FAOLSIZLIK = timedelta(days=3)  # rahbar shu qurilmada shuncha faol bo'lmasa, Telegram qayta so'raladi


def rahbar_faol_qurilma(xodim, qurilma):
    """Rahbar shu qurilmada Telegram bilan tasdiqlangan va oxirgi 3 kunda faol bo'lgan — Telegram so'ralmaydi."""
    return bool(qurilma.rahbar_faol and qurilma.rahbar_faol_xodim_id == xodim.id
                and qurilma.rahbar_faol > timezone.now() - RAHBAR_FAOLSIZLIK)


def rahbar_faolligini_yangila(xodim, qurilma):
    """To'liq kirgan rahbar uchun 3 kunlik muddat shu paytdan qayta hisoblanadi."""
    IshonchliQurilma.objects.filter(id=qurilma.id).update(rahbar_faol=timezone.now(), rahbar_faol_xodim=xodim)


def kirish_tasdiqlandimi(xodim, qurilma):
    """Telegramda «Ruxsat berish» bosilgan va so'rov aynan shu qurilmadan bo'lsa — bir martalik ruxsat."""
    return bool(KirishKodi.objects.filter(xodim=xodim, qurilma=qurilma, tasdiqlandi__isnull=False,
                                          tugaydi__gte=timezone.now()).delete()[0])


def kirish_kodini_tekshir(xodim, kod):
    k = KirishKodi.objects.filter(xodim=xodim).first()
    if not k or k.tugaydi < timezone.now() or k.urinish >= KIRISH_KODI_URINISH:
        return False
    if not check_password(str(kod), k.kod):
        k.urinish += 1
        k.save(update_fields=['urinish'])
        return False
    k.delete()  # bir martalik
    return True
