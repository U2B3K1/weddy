from django.db import transaction
from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import tolov_qabul
from apps.tenants.models import Xodim, jurnalga_yoz

from .models import BankSolishtirish, Xarajat, YopilganOy


class XarajatXatosi(Exception):
    pass


@transaction.atomic
def xarajat_kiritish(*, salon, xodim, modda, summa, sana=None, usul='naqd', izoh='', kassadan=None, filial=None):
    """Xarajat kiritish (FT-12.3, FT-13.2).

    Sotuvchi xarajatni doim kassadan chiqim sifatida kiritadi va u rahbar tasdig'ini kutadi.
    Rahbar kiritgani darhol tasdiqlangan; `kassadan=True` bo'lsa kassa smenasiga ham yoziladi.
    """
    from .moddalar import modda_bormi
    if not modda_bormi(salon, modda):
        raise XarajatXatosi("Xarajat moddasi noto'g'ri.")
    if summa <= 0:
        raise XarajatXatosi('Summa musbat bo\'lishi kerak.')
    rahbar = xodim.rol == Xodim.Rol.RAHBAR
    xsana = sana or timezone.localdate()
    if oy_yopilgan(salon, xsana.year, xsana.month):  # tuzatish va bekor qilishdagi qoida bilan bir xil
        raise XarajatXatosi("Bu oy yopilgan: avval oyni oching." if rahbar
                            else "Bu oy yopilgan: uni faqat rahbar o'zgartira oladi.")
    if kassadan is None or not rahbar:
        kassadan = True if not rahbar else False
    tolov = None
    if kassadan:
        tolov = tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.XARAJAT, summa=summa,
                            usul=usul, izoh=f'{modda}: {izoh}'.strip(': ')[:300])
        filial = tolov.smena.filial or filial  # kassadan to'langan bo'lsa — shu kassa filiali
    return Xarajat.objects.create(
        filial=filial, salon=salon, sana=sana or timezone.localdate(), modda=modda, summa=summa, usul=usul, izoh=izoh,
        kiritgan=xodim, tolov=tolov,
        holat=Xarajat.Holat.TASDIQLANDI if rahbar else Xarajat.Holat.KUTILMOQDA,
        tasdiqlagan=xodim if rahbar else None)


@transaction.atomic
def xarajat_qarori(*, salon, rahbar, xarajat, tasdiqlash, summa=None):
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise XarajatXatosi('Xarajatni faqat rahbar tasdiqlaydi.')
    xarajat = Xarajat.objects.select_for_update().get(id=xarajat.id, salon=salon)
    if xarajat.holat != Xarajat.Holat.KUTILMOQDA:
        raise XarajatXatosi('Qaror allaqachon qabul qilingan.')
    if tasdiqlash and summa is not None:  # doimiy xarajat qoralamasida summa shu oyga moslab o'zgartiriladi
        if xarajat.tolov_id:
            raise XarajatXatosi("Kassadan to'langan xarajat summasini o'zgartirib bo'lmaydi.")
        if summa <= 0:
            raise XarajatXatosi("Summa musbat bo'lishi kerak.")
        xarajat.summa = summa
    if not tasdiqlash and xarajat.tolov_id:  # rad etilsa P&L dan chiqardi, lekin pul kassadan chiqib bo'lgan
        raise XarajatXatosi("Kassadan to'langan xarajat rad etilmaydi: pul kassadan chiqqan. "
                            "Tasdiqlab, kerak bo'lsa moddasi va izohini tuzating.")
    xarajat.holat = Xarajat.Holat.TASDIQLANDI if tasdiqlash else Xarajat.Holat.RAD
    xarajat.tasdiqlagan = rahbar
    xarajat.save()
    return xarajat


def _tuzatsa_boladimi(salon, xarajat):
    """Tuzatish va bekor qilish uchun umumiy cheklovlar: yopilgan oy va bank solishtiruvi yozuvi."""
    if oy_yopilgan(salon, xarajat.sana.year, xarajat.sana.month):
        raise XarajatXatosi("Bu oy yopilgan: avval oyni oching.")
    if BankSolishtirish.objects.filter(xarajat=xarajat).exists():
        raise XarajatXatosi("Bank komissiyasi bank solishtiruvi orqali o'zgartiriladi.")


@transaction.atomic
def xarajatni_tuzatish(*, salon, rahbar, xarajat, modda=None, summa=None, sana=None, izoh=None):
    """Rahbar kiritilgan xarajatni tuzatadi. Kassadan to'langan xarajatning summasi va sanasi o'zgarmaydi —
    pul kassadan allaqachon chiqqan."""
    from .moddalar import modda_bormi
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise XarajatXatosi('Xarajatni faqat rahbar tuzatadi.')
    xarajat = Xarajat.objects.select_for_update().get(id=xarajat.id, salon=salon)
    if xarajat.holat == Xarajat.Holat.RAD:
        raise XarajatXatosi("Rad etilgan xarajat tuzatilmaydi.")
    _tuzatsa_boladimi(salon, xarajat)
    if xarajat.tolov_id and (summa not in (None, xarajat.summa) or sana not in (None, xarajat.sana)):
        raise XarajatXatosi("Kassadan to'langan xarajatning summasi va sanasini o'zgartirib bo'lmaydi.")
    if summa is not None and summa <= 0:
        raise XarajatXatosi("Summa musbat bo'lishi kerak.")
    if modda is not None and modda != xarajat.modda and not modda_bormi(salon, modda):
        raise XarajatXatosi("Xarajat moddasi noto'g'ri.")
    if sana is not None and oy_yopilgan(salon, sana.year, sana.month):
        raise XarajatXatosi("Yangi sana yopilgan oyga to'g'ri keladi.")
    eski = f'{xarajat.sana} {xarajat.modda} {xarajat.summa}'
    for nom, qiymat in (('modda', modda), ('summa', summa), ('sana', sana), ('izoh', izoh)):
        if qiymat is not None:
            setattr(xarajat, nom, qiymat)
    xarajat.save()
    jurnalga_yoz(salon, rahbar, 'xarajat_tuzatildi', f'xarajat #{xarajat.id}', eski,
                 f'{xarajat.sana} {xarajat.modda} {xarajat.summa}')
    return xarajat


@transaction.atomic
def xarajatni_bekor_qilish(*, salon, rahbar, xarajat):
    """Xarajat o'chirilmaydi — «rad etildi» holatiga o'tadi va hisobotlardan chiqadi (yozuv tarixda qoladi)."""
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise XarajatXatosi('Xarajatni faqat rahbar bekor qiladi.')
    xarajat = Xarajat.objects.select_for_update().get(id=xarajat.id, salon=salon)
    if xarajat.holat == Xarajat.Holat.RAD:
        raise XarajatXatosi('Xarajat allaqachon bekor qilingan.')
    _tuzatsa_boladimi(salon, xarajat)
    if xarajat.tolov_id:
        raise XarajatXatosi("Kassadan to'langan xarajat bekor qilinmaydi: pul kassadan chiqqan.")
    eski = xarajat.holat
    xarajat.holat, xarajat.tasdiqlagan = Xarajat.Holat.RAD, rahbar
    xarajat.save(update_fields=['holat', 'tasdiqlagan'])
    jurnalga_yoz(salon, rahbar, 'xarajat_bekor_qilindi', f'xarajat #{xarajat.id}', eski,
                 f'{xarajat.modda} {xarajat.summa}')
    return xarajat


def oy_yopilgan(salon, yil, oy):
    return YopilganOy.objects.filter(salon=salon, yil=yil, oy=oy).exists()


@transaction.atomic
def oyni_yopish(*, salon, rahbar, yil, oy):
    """Oyni yopadi (FT-18.4). Barcha tannarxlar kiritilmaguncha yopib bo'lmaydi (FT-18.6, S13)."""
    from . import reports  # reports -> models; aylanma importdan qochish

    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise XarajatXatosi('Oyni faqat rahbar yopadi.')
    _, oxiri = reports.oy_chegaralari(yil, oy)
    if oxiri >= timezone.localdate():
        raise XarajatXatosi("Tugamagan oyni yopib bo'lmaydi.")
    if oy_yopilgan(salon, yil, oy):
        raise XarajatXatosi('Bu oy allaqachon yopilgan.')
    hisobot = reports.foyda_zarar(salon, yil, oy)
    if hisobot['tannarxsiz_liboslar']:
        raise XarajatXatosi(f"{hisobot['tannarxsiz_liboslar']} ta libosning tannarxi kiritilmagan: "
                            "barcha tannarxlar kiritilmaguncha oyni yopib bo'lmaydi.")
    if hisobot['tasdiqlanmagan_xarajatlar']:
        raise XarajatXatosi(f"{hisobot['tasdiqlanmagan_xarajatlar']} ta xarajat tasdiq kutmoqda: avval ularni "
                            "tasdiqlang yoki rad eting.")
    yozuv = YopilganOy.objects.create(salon=salon, yil=yil, oy=oy, yopgan=rahbar, hisobot=hisobot)
    jurnalga_yoz(salon, rahbar, 'oy_yopildi', f'{yil}-{oy:02d}', '', f"sof foyda {hisobot['sof_foyda']}")
    return yozuv


@transaction.atomic
def oyni_ochish(*, salon, rahbar, yil, oy):
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise XarajatXatosi('Oyni faqat rahbar qayta ochadi.')
    n, _ = YopilganOy.objects.filter(salon=salon, yil=yil, oy=oy).delete()
    if not n:
        raise XarajatXatosi('Bu oy yopilmagan.')
    jurnalga_yoz(salon, rahbar, 'oy_qayta_ochildi', f'{yil}-{oy:02d}')


BANK_USULLARI = ('karta', 'click', 'payme')


def bank_holati(salon, yil, oy):
    """Har bir naqdsiz usul bo'yicha: tizimdagi tushum, bank ko'chirmasi, komissiya va farq."""
    from django.db.models import Sum

    from . import reports
    boshi, oxiri = reports.oy_chegaralari(yil, oy)
    kiritilgan = {b.usul: b for b in BankSolishtirish.objects.filter(salon=salon, yil=yil, oy=oy)}
    natija = []
    for usul in BANK_USULLARI:
        q = Tolov.objects.filter(salon=salon, usul=usul, vaqt__date__range=(boshi, oxiri))
        kirim = q.filter(tur__in=Tolov.KIRIM).aggregate(s=Sum('summa'))['s'] or 0
        chiqim = q.filter(tur__in=Tolov.CHIQIM).aggregate(s=Sum('summa'))['s'] or 0
        tizim = kirim - chiqim
        b = kiritilgan.get(usul)
        natija.append({
            'usul': usul, 'tizimda': tizim,
            'kochirma': b.kochirma_summa if b else None, 'komissiya': b.komissiya if b else None,
            # bank komissiyani ushlab qolgani uchun: kutilgan tushum = tizimdagi - komissiya
            'farq': (b.kochirma_summa - (tizim - b.komissiya)) if b else None,
        })
    return natija


@transaction.atomic
def bank_solishtirish(*, salon, rahbar, yil, oy, usul, kochirma_summa, komissiya=0):
    """Rahbar oyiga bir marta ko'chirmadagi summani kiritadi; komissiya «bank komissiyasi» xarajati bo'ladi."""
    from . import reports
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise XarajatXatosi("Bank solishtiruvini faqat rahbar kiritadi.")
    if usul not in BANK_USULLARI:
        raise XarajatXatosi("To'lov usuli noto'g'ri.")
    if komissiya < 0:
        raise XarajatXatosi("Komissiya manfiy bo'lishi mumkin emas.")
    boshi, oxiri = reports.oy_chegaralari(yil, oy)
    if boshi > timezone.localdate():
        raise XarajatXatosi("Kelgusi oy uchun bank solishtiruvi kiritilmaydi.")
    if oy_yopilgan(salon, yil, oy):  # komissiya xarajati yopilgan oyning P&L ini o'zgartirardi
        raise XarajatXatosi("Bu oy yopilgan: avval oyni oching.")
    b, _ = BankSolishtirish.objects.select_for_update().get_or_create(
        salon=salon, yil=yil, oy=oy, usul=usul, defaults={'kochirma_summa': kochirma_summa, 'kiritgan': rahbar})
    b.kochirma_summa, b.komissiya, b.kiritgan = kochirma_summa, komissiya, rahbar
    # Komissiya xarajati: qayta kiritilganda eski yozuv yangilanadi, ikki marta yozilmaydi.
    # Xarajat o'chirilmaydi — boshqa xarajatlar kabi «rad etildi» bo'lib tarixda qoladi.
    eski = Xarajat.objects.filter(id=b.xarajat_id).first() if b.xarajat_id else None
    if eski and komissiya:
        if eski.summa != komissiya or eski.holat != Xarajat.Holat.TASDIQLANDI:
            jurnalga_yoz(salon, rahbar, 'xarajat_tuzatildi', f'xarajat #{eski.id}', eski.summa, komissiya)
        eski.summa, eski.holat = komissiya, Xarajat.Holat.TASDIQLANDI
        eski.save(update_fields=['summa', 'holat'])
    elif eski:
        eski.holat = Xarajat.Holat.RAD
        eski.save(update_fields=['holat'])
        jurnalga_yoz(salon, rahbar, 'xarajat_bekor_qilindi', f'xarajat #{eski.id}', eski.summa, 'komissiya 0')
    elif komissiya:
        b.xarajat = Xarajat.objects.create(
            salon=salon, sana=min(oxiri, timezone.localdate()),
            modda=Xarajat.Modda.BANK, summa=komissiya, usul=usul,
            izoh=f'Bank komissiyasi ({usul}), {yil}-{oy:02d}', kiritgan=rahbar, tasdiqlagan=rahbar,
            holat=Xarajat.Holat.TASDIQLANDI)
    b.save()
    jurnalga_yoz(salon, rahbar, 'bank_solishtirildi', f'{yil}-{oy:02d} {usul}', '',
                 f"ko'chirma {kochirma_summa}, komissiya {komissiya}")
    return b
