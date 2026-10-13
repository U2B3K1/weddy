from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from psycopg.types.range import Range

from apps.catalog.models import Aksessuar, AksessuarDona, Libos
from apps.tenants.models import sozlama

from .models import AksessuarBron, Bron, LibosQulfi


class BandlikXatosi(Exception):
    """Libos shu sanalarga band yoki bron qilib bo'lmaydi."""


def bron_oraliq(libos, olib_ketish, qaytarish, standart_bufer=None):
    """Qaytarish kunidan keyin bufer kun ham band hisoblanadi (FT-2.4).

    Bufer: libos > kategoriya > salon sozlamasi. `standart_bufer` berilmasa sozlamadan o'qiladi
    (ro'yxat aylanayotganda bir marta o'qib uzatish kerak).
    """
    if standart_bufer is None:
        standart_bufer = sozlama(libos.salon_id).bufer_kun
    return Range(olib_ketish, qaytarish + timedelta(days=libos.samarali_bufer_kun(standart_bufer)), '[]')


def eng_yaqin_bosh_sana(libos, olib_ketish, qaytarish, bufer):
    """Band libos shu davomiylikda eng erta qachon bo'sh bo'lishi (FT-2.2, S27). Topilmasa None."""
    davom = qaytarish - olib_ketish
    nomzod = olib_ketish
    for _ in range(60):
        oraliq = bron_oraliq(libos, nomzod, nomzod + davom, bufer)
        tosiq = (Bron.faol().filter(libos=libos, oraliq__overlap=oraliq).order_by('-oraliq__endswith').first())
        if not tosiq:
            return nomzod
        nomzod = tosiq.oraliq.upper  # yuqori chegara kirmaydi: bron va bufer tugagandan keyingi birinchi kun
    return None


def bosh_liboslar(salon, olib_ketish, qaytarish, bandlarni_korsat=False, xodim=None, q=''):
    """Tanlangan oraliqda bo'sh liboslar (FT-2.2, FT-2.3).

    `bandlarni_korsat=True` bo'lsa, band liboslar ham `(libos, band)` ko'rinishida qaytadi.
    `q` — artikul yoki nom bo'yicha qidiruv: unda band libos har doim chiqadi (FT-2.2).
    Band libosga `eng_yaqin_bosh` (sana yoki None) qo'yiladi.
    """
    liboslar = (Libos.objects.filter(salon=salon, holat=Libos.Holat.BOSH)
                .select_related('kategoriya').prefetch_related('rasmlar'))
    q = (q or '').strip()
    if q:
        liboslar = liboslar.filter(Q(artikul__icontains=q) | Q(nomi__icontains=q))
        bandlarni_korsat = True
    natija = []
    bufer = sozlama(salon).bufer_kun
    for libos in liboslar:
        oraliq = bron_oraliq(libos, olib_ketish, qaytarish, bufer)
        band = Bron.faol().filter(salon=salon, libos=libos, oraliq__overlap=oraliq).exists()
        if not band or bandlarni_korsat:
            libos.qulflangan = (not band and xodim is not None
                                and boshqa_qulf(libos, oraliq, xodim).exists())
            libos.eng_yaqin_bosh = eng_yaqin_bosh_sana(libos, olib_ketish, qaytarish, bufer) if band else None
            natija.append((libos, band))
    return natija


@transaction.atomic
def bron_qilish(*, salon, libos, olib_ketish, qaytarish, xodim, avans_bor=False, zakaz=None):
    """Libosni sanalarga band qiladi. Ikki marta bron bazadagi cheklov bilan ham to'xtatiladi."""
    if qaytarish < olib_ketish:
        raise BandlikXatosi('Qaytarish sanasi olib ketishdan oldin bo\'lishi mumkin emas.')
    if libos.salon_id != salon.id or libos.holat != Libos.Holat.BOSH:
        raise BandlikXatosi('Libos mavjud emas yoki bron qilib bo\'lmaydi.')

    oraliq = bron_oraliq(libos, olib_ketish, qaytarish)
    if boshqa_qulf(libos, oraliq, xodim).exists():
        raise BandlikXatosi("Hozir boshqa sotuvchi rasmiylashtiryapti.")
    # Muddati o'tgan vaqtinchalik bronlar libosni band ushlab turmasligi uchun o'chiriladi (FT-2.5).
    Bron.objects.filter(salon=salon, libos=libos, oraliq__overlap=oraliq,
                        turi=Bron.Turi.VAQTINCHALIK, muddati__lt=timezone.now()).delete()
    try:
        with transaction.atomic():
            return Bron.objects.create(
                salon=salon, libos=libos, oraliq=oraliq, yaratgan=xodim, zakaz=zakaz,
                turi=Bron.Turi.MUSTAHKAM if avans_bor else Bron.Turi.VAQTINCHALIK,
                muddati=None if avans_bor else timezone.now() + timedelta(
                    hours=sozlama(salon).vaqtinchalik_bron_soat),
            )
    except IntegrityError:
        raise BandlikXatosi('Libos shu sanalarga band bo\'lib qoldi.')


def boshqa_qulf(libos, oraliq, xodim):
    """Boshqa xodim qo'ygan, muddati o'tmagan qulflar."""
    return (LibosQulfi.objects.filter(libos=libos, oraliq__overlap=oraliq, tugaydi__gt=timezone.now())
            .exclude(xodim=xodim))


@transaction.atomic
def qulflash(*, salon, libos, olib_ketish, qaytarish, xodim):
    """Libosni shu sanalar uchun xodimga qulflaydi. Band yoki boshqa xodimda qulf bo'lsa xato."""
    libos = Libos.objects.select_for_update().get(id=libos.id, salon=salon)  # qulflash poygasiga qarshi
    oraliq = bron_oraliq(libos, olib_ketish, qaytarish)
    if Bron.faol().filter(salon=salon, libos=libos, oraliq__overlap=oraliq).exists():
        raise BandlikXatosi("Libos shu sanalarga band.")
    if boshqa_qulf(libos, oraliq, xodim).exists():
        raise BandlikXatosi("Hozir boshqa sotuvchi rasmiylashtiryapti.")
    LibosQulfi.objects.filter(libos=libos, xodim=xodim).delete()
    return LibosQulfi.objects.create(
        salon=salon, libos=libos, oraliq=oraliq, xodim=xodim,
        tugaydi=timezone.now() + timedelta(minutes=sozlama(salon).qulf_daqiqa))


def qulfni_olish(libos, xodim):
    LibosQulfi.objects.filter(libos=libos, xodim=xodim).delete()


# --- Aksessuarlar (4.4): har bir dona alohida band qilinadi ---

def aksessuar_oraliq(aksessuar, olib_ketish, qaytarish, standart_bufer=None):
    if aksessuar.kategoriya.bufer_kun is not None:
        bufer = aksessuar.kategoriya.bufer_kun
    else:
        bufer = sozlama(aksessuar.salon_id).bufer_kun if standart_bufer is None else standart_bufer
    return Range(olib_ketish, qaytarish + timedelta(days=bufer), '[]')


def bosh_donalar(aksessuar, oraliq):
    """Oraliqda band bo'lmagan, ishlatishga yaroqli donalar (yorliq tartibida)."""
    band = AksessuarBron.faol().filter(oraliq__overlap=oraliq).values('dona_id')
    return list(aksessuar.donalar.filter(holat=AksessuarDona.Holat.BOSH).exclude(id__in=band))


def bosh_aksessuarlar(salon, olib_ketish, qaytarish):
    """[(aksessuar, bo'sh donalar soni)] — kamida bitta bo'sh donasi borlari (FT-4.2)."""
    natija = []
    bufer = sozlama(salon).bufer_kun
    for a in (Aksessuar.objects.filter(salon=salon, holat=Aksessuar.Holat.FAOL)
              .select_related('kategoriya').order_by('kategoriya__tartib', 'nomi')):
        soni = len(bosh_donalar(a, aksessuar_oraliq(a, olib_ketish, qaytarish, bufer)))
        if soni:
            natija.append((a, soni))
    return natija


@transaction.atomic
def aksessuar_bron_qilish(*, salon, aksessuar, soni, olib_ketish, qaytarish, avans_bor=False, zakaz=None):
    """Aksessuardan `soni` dona band qiladi va band qilingan donalarni qaytaradi.

    Yetarli bo'sh dona bo'lmasa hech narsa band qilinmaydi. Poyga holatida bazadagi cheklov
    ushlagan donadan keyingisi sinab ko'riladi.
    """
    if aksessuar.salon_id != salon.id or aksessuar.holat != Aksessuar.Holat.FAOL:
        raise BandlikXatosi('Aksessuar mavjud emas.')
    if soni < 1:
        raise BandlikXatosi("Aksessuar soni kamida 1 bo'lishi kerak.")
    if qaytarish < olib_ketish:
        raise BandlikXatosi("Qaytarish sanasi olib ketishdan oldin bo'lishi mumkin emas.")
    oraliq = aksessuar_oraliq(aksessuar, olib_ketish, qaytarish)
    AksessuarBron.objects.filter(
        dona__aksessuar=aksessuar, oraliq__overlap=oraliq, turi=Bron.Turi.VAQTINCHALIK,
        muddati__lt=timezone.now()).delete()
    olingan = []
    donalar = bosh_donalar(aksessuar, oraliq)
    if zakaz is not None and zakaz.filial_id:  # avval shu filialdagi, keyin biriktirilmagan, oxirida boshqa filialdagi dona
        donalar.sort(key=lambda d: 0 if d.filial_id == zakaz.filial_id else 1 if d.filial_id is None else 2)
    for dona in donalar:
        try:
            with transaction.atomic():
                AksessuarBron.objects.create(
                    salon=salon, dona=dona, oraliq=oraliq, zakaz=zakaz,
                    turi=Bron.Turi.MUSTAHKAM if avans_bor else Bron.Turi.VAQTINCHALIK,
                    muddati=None if avans_bor else timezone.now() + timedelta(
                        hours=sozlama(salon).vaqtinchalik_bron_soat))
            olingan.append(dona)
        except IntegrityError:
            continue
        if len(olingan) == soni:
            return olingan
    raise BandlikXatosi(f"«{aksessuar.nomi}» aksessuaridan {soni} dona bo'sh emas.")
