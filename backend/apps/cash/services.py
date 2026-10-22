from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.bookings.models import AksessuarBron, Bron
from apps.orders.models import Zakaz

from .models import Smena, SmenaIshtirokchi, Tolov


class KassaXatosi(Exception):
    pass


def ochiq_smena(salon, filial=False):
    """Ochiq smena. `filial` berilmasa — salondagi istalgan ochiq smena (bitta kassali salon);
    filial obyekti yoki None berilsa — aynan shu kassaning (None — umumiy kassa) smenasi."""
    qs = Smena.objects.filter(salon=salon, yopilgan__isnull=True)
    if filial is not False:
        qs = qs.filter(filial=filial)
    return qs.order_by('id').first()


def xodim_smenasi(salon, xodim):
    """Xodim hozir ishlayotgan ochiq smena. To'lov shu kassaga yoziladi — filial kassalarida ham adashmaydi."""
    ish = (SmenaIshtirokchi.objects.filter(salon=salon, xodim=xodim, chiqqan=None, smena__yopilgan__isnull=True)
           .select_related('smena').order_by('-id').first())
    return ish.smena if ish else None


def _kassa(salon, xodim, filial):
    """Amal bajariladigan smena: xodim ishlayotgani, bo'lmasa shu filial (yoki umumiy) kassasining ochiq smenasi."""
    return xodim_smenasi(salon, xodim) or ochiq_smena(salon, filial)


@transaction.atomic
def smena_ochish(*, salon, xodim, boshlangich_qoldiq, filial=None):
    """Birinchi kelgan sotuvchi smenani ochadi va boshlang'ich qoldiqni tasdiqlaydi (FT-12.7)."""
    boshqa = xodim_smenasi(salon, xodim)
    if boshqa and boshqa.filial_id != (filial.id if filial else None):
        raise KassaXatosi('Siz boshqa kassaning ochiq smenasidasiz: avval undan chiqing.')
    try:
        with transaction.atomic():
            smena = Smena.objects.create(salon=salon, sana=timezone.localdate(), ochgan=xodim,
                                         boshlangich_qoldiq=boshlangich_qoldiq, filial=filial)
    except IntegrityError:
        raise KassaXatosi('Smena allaqachon ochiq. Unga qo\'shiling.')
    SmenaIshtirokchi.objects.create(salon=salon, smena=smena, xodim=xodim)
    return smena


@transaction.atomic
def smenaga_qoshilish(*, salon, xodim, filial=None):
    smena = ochiq_smena(salon, filial)
    if not smena:
        raise KassaXatosi('Ochiq smena yo\'q.')
    boshqa = xodim_smenasi(salon, xodim)
    if boshqa and boshqa.id != smena.id:
        raise KassaXatosi('Siz boshqa kassaning ochiq smenasidasiz: avval undan chiqing.')
    smena = _qulfla(smena)  # ikki marta bosilsa ikkinchi ishtirokchi qatori yaratilmaydi (yopish «oxirgi emas» deb to'xtardi)
    SmenaIshtirokchi.objects.get_or_create(salon=salon, smena=smena, xodim=xodim, chiqqan=None)
    return smena


def _qulfla(smena):
    """Smena qatorini qulflaydi va hali ochiqligini tekshiradi. To'lov, chiqish va yopish shu qulf orqali
    navbatma-navbat bajariladi: yopilayotgan smenaga to'lov tushmaydi (aks holda saqlangan qoldiq va farq
    unga kirmay qolardi), ikki sotuvchi bir vaqtda «oxirgi emasman» deb chiqib ketmaydi."""
    smena = Smena.objects.select_for_update().get(id=smena.id)
    if smena.yopilgan:
        raise KassaXatosi('Smena yopilgan.')
    return smena


def _faol_ishtirokchi(smena, xodim):
    return SmenaIshtirokchi.objects.filter(smena=smena, xodim=xodim, chiqqan=None).exists()


def _bronlar_joyida(zakaz):
    """Zakazning har bir libosi va aksessuar donasi uchun bron qatori bor (muddati o'tgan bo'lsa ham — u hali
    boshqaga berilmagan, avans bilan mustahkam bo'ladi). Qator yo'q bo'lsa — boshqa zakaz olgan."""
    return (Bron.objects.filter(zakaz=zakaz).count() == zakaz.pozitsiyalar.count()
            and AksessuarBron.objects.filter(zakaz=zakaz).count() == zakaz.aksessuarlar.count())


def tolangan_summa(zakaz):
    r = zakaz.tolovlar.filter(tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ]).aggregate(s=Sum('summa'))
    return r['s'] or 0


@transaction.atomic
def tolov_qabul(*, salon, xodim, tur, summa, usul=Tolov.Usul.NAQD, zakaz=None, izoh=''):
    """To'lov, zalog yoki chiqim yozadi. Ochiq smena va smenadagi xodim shart (FT-12.7, FT-12.8).

    Avans zakazni mustahkam bronga o'tkazadi; avans + qoldiq jamiga yetsa, zakaz to'liq to'langan
    kuni belgilanadi — daromad shu kuni tan olinadi (6.1).
    """
    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ):
        if zakaz is None:
            raise KassaXatosi('Zakaz ko\'rsatilmagan.')
        # Qulf tartibi hamma joyda bir xil: avval zakaz, keyin smena (bekor qilish, berish, qaytarish ham shunday) —
        # aks holda parallel avans va bekor qilish bir-birini kutib qolardi (deadlock)
        zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    # To'liq bepul zakaz (100% chegirma/promokod): bron 0 so'mlik avans bilan tasdiqlanadi
    bepul_bron = tur == Tolov.Tur.AVANS and summa == 0 and zakaz is not None and zakaz.jami == 0
    if summa <= 0 and not bepul_bron:
        raise KassaXatosi('Summa musbat bo\'lishi kerak.')
    smena = xodim_smenasi(salon, xodim)
    if not smena:
        if not ochiq_smena(salon):
            raise KassaXatosi('Ochiq smena bo\'lmasa to\'lov qabul qilinmaydi.')
        raise KassaXatosi('Avval smenaga qo\'shiling.')
    smena = _qulfla(smena)

    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ):
        if zakaz.holat in (Zakaz.Holat.BEKOR, Zakaz.Holat.YOPILDI):
            raise KassaXatosi('Bu zakazga to\'lov qabul qilib bo\'lmaydi.')
        if zakaz.holat == Zakaz.Holat.CHEGIRMA_KUTILMOQDA:
            raise KassaXatosi('Chegirma tasdig\'i kutilmoqda.')
        if tur == Tolov.Tur.QOLDIQ and tolangan_summa(zakaz) == 0:
            raise KassaXatosi('Avval avans kiritiladi.')
        if tolangan_summa(zakaz) + summa > zakaz.jami:
            raise KassaXatosi('To\'lov zakaz summasidan oshib ketadi.')
        if tur == Tolov.Tur.AVANS and zakaz.holat == Zakaz.Holat.VAQTINCHALIK and not _bronlar_joyida(zakaz):
            raise KassaXatosi("Vaqtinchalik bron muddati o'tib, libos yoki aksessuar boshqa zakazga berilgan. "
                              "Bu zakazni bekor qilib, qaytadan rasmiylashtiring.")

    tolov = Tolov.objects.create(salon=salon, smena=smena, zakaz=zakaz, tur=tur, usul=usul,
                                 summa=summa, xodim=xodim, izoh=izoh)

    if tur == Tolov.Tur.AVANS and zakaz.holat == Zakaz.Holat.VAQTINCHALIK:
        zakaz.holat = Zakaz.Holat.BRON
        Bron.objects.filter(zakaz=zakaz).update(turi=Bron.Turi.MUSTAHKAM, muddati=None)
        AksessuarBron.objects.filter(zakaz=zakaz).update(turi=Bron.Turi.MUSTAHKAM, muddati=None)
    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ) and tolangan_summa(zakaz) == zakaz.jami:
        zakaz.tolangan_sana = timezone.localdate()
    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ):
        zakaz.save(update_fields=['holat', 'tolangan_sana'])
    return tolov


def kassa_hisobot(smena):
    """Kunlik kassa hisoboti, naqd pul bo'yicha (4.12 jadvali, Ilova C.2)."""
    q = smena.tolovlar.filter(usul=Tolov.Usul.NAQD)

    def jami(*turlar):
        return q.filter(tur__in=turlar).aggregate(s=Sum('summa'))['s'] or 0

    tushum = jami(Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA)
    zalog_olingan = jami(Tolov.Tur.ZALOG)
    zalog_qaytgan = jami(Tolov.Tur.ZALOG_QAYTARISH)
    xarajat = jami(Tolov.Tur.XARAJAT)
    vozvrat = jami(Tolov.Tur.VOZVRAT, Tolov.Tur.INKASSATSIYA)
    hisobdagi = smena.boshlangich_qoldiq + tushum + zalog_olingan - zalog_qaytgan - xarajat - vozvrat
    sotuvchilar = {}
    for t in smena.tolovlar.filter(tur__in=Tolov.KIRIM).select_related('xodim'):
        sotuvchilar[t.xodim.ism] = sotuvchilar.get(t.xodim.ism, 0) + t.summa
    return {
        'kun_boshidagi_qoldiq': smena.boshlangich_qoldiq, 'tushum': tushum,
        'olingan_zaloglar': zalog_olingan, 'qaytarilgan_zaloglar': zalog_qaytgan,
        'xarajatlar': xarajat, 'vozvrat_va_inkassatsiya': vozvrat,
        'hisobdagi_qoldiq': hisobdagi, 'fakt_qoldiq': smena.fakt_qoldiq,
        'farq': smena.farq, 'sotuvchilar': sotuvchilar,
    }


@transaction.atomic
def smena_chiqish(*, salon, xodim, sanalgan_summa, filial=None):
    """Sotuvchi kun o'rtasida ketadi: naqd sanaladi, farq ketayotganga yoziladi (FT-12.9)."""
    smena = _kassa(salon, xodim, filial)
    if not smena:
        raise KassaXatosi('Ochiq smena yo\'q.')
    smena = _qulfla(smena)
    faol = SmenaIshtirokchi.objects.filter(smena=smena, chiqqan=None)
    if faol.count() < 2:
        raise KassaXatosi('Siz oxirgi sotuvchisiz: smenani yoping.')
    ish = faol.filter(xodim=xodim).first()
    if not ish:
        raise KassaXatosi('Siz smenada emassiz.')
    hisobdagi = kassa_hisobot(smena)['hisobdagi_qoldiq']
    ish.chiqqan = timezone.now()
    ish.sanalgan_summa = sanalgan_summa
    ish.farq = sanalgan_summa - hisobdagi
    ish.save()
    return ish


@transaction.atomic
def smena_yopish(*, salon, xodim, fakt_qoldiq, izoh='', filial=None):
    """Oxirgi qolgan sotuvchi naqd pulni sanab yopadi; farq bo'lsa izoh majburiy (FT-12.10)."""
    smena = _kassa(salon, xodim, filial)
    if not smena:
        raise KassaXatosi('Ochiq smena yo\'q.')
    smena = _qulfla(smena)
    faol = SmenaIshtirokchi.objects.filter(smena=smena, chiqqan=None)
    if faol.count() != 1 or not faol.filter(xodim=xodim).exists():
        raise KassaXatosi('Smenani faqat oxirgi qolgan sotuvchi yopadi.')
    hisobdagi = kassa_hisobot(smena)['hisobdagi_qoldiq']
    farq = fakt_qoldiq - hisobdagi
    if farq != 0 and not izoh.strip():
        raise KassaXatosi('Kassa farqi bor: izoh majburiy.')
    smena.hisobdagi_qoldiq, smena.fakt_qoldiq, smena.farq = hisobdagi, fakt_qoldiq, farq
    smena.izoh, smena.yopilgan = izoh, timezone.now()
    from .tekshiruv import yopishda_zalog_hisobi
    zalog_xabari = yopishda_zalog_hisobi(smena)  # FT-12.5: tekshirilmagan zalog bo'lsa rahbar biladi
    smena.save()
    if zalog_xabari:
        from apps.notify.services import rahbarlarga
        rahbarlarga(salon, 'zalog_tekshirilmadi', zalog_xabari)
    faol.update(chiqqan=smena.yopilgan)
    if farq != 0:  # FT-12.10: farq bo'lsa rahbarga darhol xabar
        from apps.notify.services import rahbarlarga, som
        rahbarlarga(salon, 'kassa_farqi',
                    f"Kassa farqi: {som(farq)}{' · ' + smena.filial.nomi if smena.filial_id else ''}\n"
                    f"Smena {smena.sana:%d.%m.%Y}, yopdi: {xodim.ism}.\n"
                    f"Hisobda {som(hisobdagi)}, sanaldi {som(fakt_qoldiq)}.\nIzoh: {izoh}")
    return smena
