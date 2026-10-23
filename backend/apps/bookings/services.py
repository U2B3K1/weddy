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


# Yangi zakazga faqat «bo'sh» libos (tozalashdagi va ta'mirdagi libos ro'yxatda chiqmaydi — talab).
# Lekin MAVJUD zakazni ko'chirishda libosning bugungi vaqtinchalik holati (tozalash, ta'mir) to'siq emas:
# ta'mir kelgusi bronlarni saqlaydi (tamir.py), ko'chirish ham o'sha bronni boshqa sanaga o'tkazadi xolos.
QAYTA_BRONLANADI = (Libos.Holat.BOSH, Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA)


def bron_oraliq(libos, olib_ketish, qaytarish, standart_bufer=None):
    """Qaytarish kunidan keyin bufer kun ham band hisoblanadi (FT-2.4).

    Bufer: libos > kategoriya > salon sozlamasi. `standart_bufer` berilmasa sozlamadan o'qiladi
    (ro'yxat aylanayotganda bir marta o'qib uzatish kerak).
    """
    if standart_bufer is None:
        standart_bufer = sozlama(libos.salon_id).bufer_kun
    return Range(olib_ketish, qaytarish + timedelta(days=libos.samarali_bufer_kun(standart_bufer)), '[]')


def eng_yaqin_bosh_sana(libos, olib_ketish, qaytarish, bufer, bronlar):
    """Band libos shu davomiylikda eng erta qachon bo'sh bo'lishi (FT-2.2, S27). Topilmasa None.

    `bronlar` — libosning `olib_ketish` dan keyin tugaydigan faol bron oraliqlari (ro'yxat aylanayotganda
    bir martada olib uzatiladi).
    """
    davom = qaytarish - olib_ketish
    nomzod = olib_ketish
    for _ in range(60):
        oraliq = bron_oraliq(libos, nomzod, nomzod + davom, bufer)
        tosiqlar = [b for b in bronlar if _kesishadi(oraliq, b)]
        if not tosiqlar:
            return nomzod
        # yuqori chegara kirmaydi: bron va bufer tugagandan keyingi birinchi kun
        nomzod = max(_chegaralar(b)[1] for b in tosiqlar)
    return None


def _chegaralar(r):
    """Sana oralig'i `[boshi, oxiri)` ko'rinishida — chegaralar `[]` yoki `[)` bo'lishi mumkin."""
    return ((r.lower if r.lower_inc else r.lower + timedelta(days=1)),
            (r.upper + timedelta(days=1) if r.upper_inc else r.upper))


def _kesishadi(a, b):
    """Ikki sana oralig'i kesishadimi (PostgreSQL `&&` kabi)."""
    a1, a2 = _chegaralar(a)
    b1, b2 = _chegaralar(b)
    return a1 < b2 and b1 < a2


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
    liboslar = list(liboslar)
    if not liboslar:
        return natija
    # Har libosga alohida so'rov o'rniga (yuzlab libosda sekin edi): eng katta bufer bilan qamrovchi oraliqdagi
    # bronlar va qulflar bir martada olinadi, har libosning o'z oralig'i bilan kesishishi shu yerda tekshiriladi.
    qamrov = Range(olib_ketish, qaytarish + timedelta(days=max(l.samarali_bufer_kun(bufer) for l in liboslar)), '[]')
    bronlar, qulflar = {}, {}
    for libos_id, b_oraliq in (Bron.faol().filter(salon=salon, libos__in=liboslar, oraliq__overlap=qamrov)
                               .values_list('libos_id', 'oraliq')):
        bronlar.setdefault(libos_id, []).append(b_oraliq)
    if xodim is not None:
        for libos_id, q_oraliq in (LibosQulfi.objects.filter(libos__in=liboslar, oraliq__overlap=qamrov,
                                                             tugaydi__gt=timezone.now())
                                   .exclude(xodim=xodim).values_list('libos_id', 'oraliq')):
            qulflar.setdefault(libos_id, []).append(q_oraliq)
    keyingi = {}  # band liboslarning eng yaqin bo'sh sanasi uchun qamrovdan keyingi bronlar ham kerak
    if bandlarni_korsat and bronlar:
        for libos_id, b_oraliq in (Bron.faol().filter(salon=salon, libos_id__in=list(bronlar),
                                                      oraliq__endswith__gt=olib_ketish)
                                   .values_list('libos_id', 'oraliq')):
            keyingi.setdefault(libos_id, []).append(b_oraliq)
    for libos in liboslar:
        oraliq = bron_oraliq(libos, olib_ketish, qaytarish, bufer)
        band = any(_kesishadi(oraliq, b) for b in bronlar.get(libos.id, ()))
        if not band or bandlarni_korsat:
            libos.qulflangan = not band and any(_kesishadi(oraliq, q) for q in qulflar.get(libos.id, ()))
            libos.eng_yaqin_bosh = (eng_yaqin_bosh_sana(libos, olib_ketish, qaytarish, bufer,
                                                        keyingi.get(libos.id, [])) if band else None)
            natija.append((libos, band))
    return natija


@transaction.atomic
def bron_qilish(*, salon, libos, olib_ketish, qaytarish, xodim, avans_bor=False, zakaz=None, qayta=False, muddati=None):
    """Libosni sanalarga band qiladi. Ikki marta bron bazadagi cheklov bilan ham to'xtatiladi.

    `qayta=True` — mavjud zakazning o'sha libosini yangi sanaga ko'chirish (QAYTA_BRONLANADI).
    `muddati` — avanssiz bronning eski muddati: ko'chirish/almashtirish uni uzaytirmasin (FT-2.5).
    """
    if qaytarish < olib_ketish:
        raise BandlikXatosi('Qaytarish sanasi olib ketishdan oldin bo\'lishi mumkin emas.')
    if libos.salon_id != salon.id or libos.holat not in (QAYTA_BRONLANADI if qayta else (Libos.Holat.BOSH,)):
        raise BandlikXatosi('Libos mavjud emas yoki bron qilib bo\'lmaydi.')

    oraliq = bron_oraliq(libos, olib_ketish, qaytarish)
    if boshqa_qulf(libos, oraliq, xodim).exists():
        raise BandlikXatosi("Hozir boshqa sotuvchi rasmiylashtiryapti.")
    # Muddati o'tgan vaqtinchalik bronlar libosni band ushlab turmasligi uchun o'chiriladi (FT-2.5).
    _muddati_otganlarni_boshat(Bron.objects.filter(salon=salon, libos=libos, oraliq__overlap=oraliq,
                                                  turi=Bron.Turi.VAQTINCHALIK, muddati__lt=timezone.now()), zakaz)
    try:
        with transaction.atomic():
            return Bron.objects.create(
                salon=salon, libos=libos, oraliq=oraliq, yaratgan=xodim, zakaz=zakaz,
                turi=Bron.Turi.MUSTAHKAM if avans_bor else Bron.Turi.VAQTINCHALIK,
                muddati=None if avans_bor else muddati or _yangi_muddat(salon),
            )
    except IntegrityError:
        raise BandlikXatosi('Libos shu sanalarga band bo\'lib qoldi.')


def _yangi_muddat(salon):
    return timezone.now() + timedelta(hours=sozlama(salon).vaqtinchalik_bron_soat)


def _muddati_otganlarni_boshat(bronlar, zakaz=None):
    """Muddati o'tgan vaqtinchalik bronlarni bo'shatadi. Bron zakazga tegishli bo'lsa zakazning o'zi bekor qilinadi
    (cron kabi) — aks holda u bronsiz «vaqtinchalik» bo'lib qolar va keyin avans olib, band libosni ikkinchi marta bron qilardi."""
    from apps.orders.changes import muddati_otganlarni_bekor_qil
    zakaz_idlar = set(bronlar.exclude(zakaz__isnull=True).values_list('zakaz_id', flat=True)) - {getattr(zakaz, 'id', None)}
    if zakaz_idlar:
        muddati_otganlarni_bekor_qil(zakaz_idlar=zakaz_idlar)
    bronlar.delete()  # zakazsiz va (pul olingani uchun) bekor qilinmagan zakazlarning muddati o'tgan bronlari


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


# Libosdagi QAYTA_BRONLANADI kabi: mavjud zakazni ko'chirishda donaning bugungi ta'miri to'siq emas
QAYTA_BRONLANADI_DONA = (AksessuarDona.Holat.BOSH, AksessuarDona.Holat.TAMIRDA)


def bosh_donalar(aksessuar, oraliq, holatlar=(AksessuarDona.Holat.BOSH,)):
    """Oraliqda band bo'lmagan, ishlatishga yaroqli donalar (yorliq tartibida)."""
    band = AksessuarBron.faol().filter(oraliq__overlap=oraliq).values('dona_id')
    return list(aksessuar.donalar.filter(holat__in=holatlar).exclude(id__in=band))


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
def aksessuar_bron_qilish(*, salon, aksessuar, soni, olib_ketish, qaytarish, avans_bor=False, zakaz=None,
                          qayta=False, avvalgi=(), muddati=None):
    """Aksessuardan `soni` dona band qiladi va band qilingan donalarni qaytaradi.

    Yetarli bo'sh dona bo'lmasa hech narsa band qilinmaydi. Poyga holatida bazadagi cheklov
    ushlagan donadan keyingisi sinab ko'riladi. `qayta=True` — mavjud zakazni ko'chirish: ta'mirdagi dona ham
    olinadi va zakazning `avvalgi` donalari birinchi sinaladi (mijoz o'sha donani ko'rgan bo'lishi mumkin).
    """
    if aksessuar.salon_id != salon.id or aksessuar.holat != Aksessuar.Holat.FAOL:
        raise BandlikXatosi('Aksessuar mavjud emas.')
    if soni < 1:
        raise BandlikXatosi("Aksessuar soni kamida 1 bo'lishi kerak.")
    if qaytarish < olib_ketish:
        raise BandlikXatosi("Qaytarish sanasi olib ketishdan oldin bo'lishi mumkin emas.")
    oraliq = aksessuar_oraliq(aksessuar, olib_ketish, qaytarish)
    _muddati_otganlarni_boshat(AksessuarBron.objects.filter(
        dona__aksessuar=aksessuar, oraliq__overlap=oraliq, turi=Bron.Turi.VAQTINCHALIK,
        muddati__lt=timezone.now()), zakaz)
    olingan = []
    donalar = bosh_donalar(aksessuar, oraliq, QAYTA_BRONLANADI_DONA if qayta else (AksessuarDona.Holat.BOSH,))
    if zakaz is not None and zakaz.filial_id:  # avval shu filialdagi, keyin biriktirilmagan, oxirida boshqa filialdagi dona
        donalar.sort(key=lambda d: 0 if d.filial_id == zakaz.filial_id else 1 if d.filial_id is None else 2)
    avvalgi = {d.id for d in avvalgi}
    donalar.sort(key=lambda d: d.id not in avvalgi)  # barqaror saralash: filial tartibi saqlanadi
    for dona in donalar:
        try:
            with transaction.atomic():
                AksessuarBron.objects.create(
                    salon=salon, dona=dona, oraliq=oraliq, zakaz=zakaz,
                    turi=Bron.Turi.MUSTAHKAM if avans_bor else Bron.Turi.VAQTINCHALIK,
                    muddati=None if avans_bor else muddati or _yangi_muddat(salon))
            olingan.append(dona)
        except IntegrityError:
            continue
        if len(olingan) == soni:
            return olingan
    raise BandlikXatosi(f"«{aksessuar.nomi}» aksessuaridan {soni} dona bo'sh emas.")
