from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.tenants.models import Xodim, jurnalga_yoz, sozlama

from .models import Aksessuar, AksessuarDona, Libos


class KatalogXatosi(Exception):
    pass


def _rahbar(xodim):
    return xodim.rol == Xodim.Rol.RAHBAR


@transaction.atomic
def libos_qoshish(*, salon, xodim, artikul, nomi, kategoriya, olcham='', rang='', ijara_narxi=0,
                  zalog=0, tannarx=None):
    """Libos qo'shish (FT-3.5, FT-3.6).

    Sotuvchi tannarxni kiritmaydi va ko'rmaydi; uning libosi «Tasdiq kutilmoqda» holatida bo'ladi va
    zakazda ko'rinmaydi. Rahbar qo'shgani darhol katalogga chiqadi.
    """
    if kategoriya.salon_id != salon.id or kategoriya.turi != kategoriya.Turi.LIBOS:
        raise KatalogXatosi('Kategoriya topilmadi.')
    rahbar = _rahbar(xodim)
    soz = sozlama(salon)
    if not rahbar and not soz.sotuvchi_libos_qoshadi:
        raise KatalogXatosi("Libosni faqat rahbar qo'shadi (sozlamalarda belgilangan).")
    if not rahbar:
        tannarx = None  # sotuvchi tannarx kirita olmaydi
    try:
        with transaction.atomic():
            libos = Libos.objects.create(
                salon=salon, artikul=artikul.strip(), nomi=nomi.strip(), kategoriya=kategoriya,
                olcham=olcham, rang=rang, ijara_narxi=ijara_narxi, zalog=zalog, tannarx=tannarx,
                qoshgan=xodim,
                # tasdiq o'chirilgan bo'lsa sotuvchi libosi darhol katalogga chiqadi (FT-3.6, S23)
                holat=(Libos.Holat.BOSH if rahbar or not soz.libos_tasdigi
                       else Libos.Holat.TASDIQ_KUTILMOQDA))
    except IntegrityError:
        raise KatalogXatosi(f'«{artikul}» artikuli salonda allaqachon bor.')
    jurnalga_yoz(salon, xodim, 'libos_qoshildi', f'libos {libos.artikul}', '',
                 f'{libos.nomi}, narx {ijara_narxi}, holat {libos.holat}')
    if not rahbar:  # FT-3.6: sotuvchi qo'shgan libos haqida rahbarga xabar (tasdiq yoqilmagan bo'lsa ham)
        from apps.notify.services import rahbarlarga
        rahbarlarga(salon, 'yangi_libos',
                    f"{xodim.ism} yangi libos qo'shdi: {libos.artikul} {libos.nomi}.\n"
                    + ("Narx va tannarxni kiritib tasdiqlang." if libos.holat == Libos.Holat.TASDIQ_KUTILMOQDA
                       else "Libos katalogda; tannarxni kiriting."))
    return libos


@transaction.atomic
def libosni_tasdiqlash(*, salon, rahbar, libos, ijara_narxi, tannarx, zalog=None):
    """Rahbar ijara narxi va tannarxni kiritib tasdiqlaydi; libos katalogga chiqadi (FT-3.6)."""
    if not _rahbar(rahbar):
        raise KatalogXatosi('Libosni faqat rahbar tasdiqlaydi.')
    libos = Libos.objects.select_for_update().get(id=libos.id, salon=salon)
    if libos.holat != Libos.Holat.TASDIQ_KUTILMOQDA:
        raise KatalogXatosi('Libos tasdiq kutmayapti.')
    if tannarx is None:
        raise KatalogXatosi('Tannarx majburiy.')
    eski = libos.ijara_narxi
    libos.ijara_narxi, libos.tannarx, libos.holat = ijara_narxi, tannarx, Libos.Holat.BOSH
    if zalog is not None:
        libos.zalog = zalog
    libos.save()
    jurnalga_yoz(salon, rahbar, 'libos_tasdiqlandi', f'libos {libos.artikul}', f'narx {eski}',
                 f'narx {ijara_narxi}, tannarx {tannarx}')
    return libos


# Qo'lda o'tkaziladigan holatlar (FT-3.9); «bosh/tozalashda» zakaz jarayonida o'zi o'zgaradi
# «Ta'mirda» holati faqat ta'mir jurnali orqali (catalog/tamir.py), shunda sana, narx va kunlar yoziladi
QOLDA_HOLATLAR = (Libos.Holat.BOSH, Libos.Holat.SOTILDI,
                  Libos.Holat.HISOBDAN_CHIQARILDI, Libos.Holat.ARXIV)


@transaction.atomic
def libosni_ozgartirish(*, salon, rahbar, libos, **maydonlar):
    """Rahbar narx, tannarx, zalog yoki holatni o'zgartiradi; narx o'zgarishi jurnalga (FT-3.7)."""
    if not _rahbar(rahbar):
        raise KatalogXatosi("Narx va tannarxni faqat rahbar o'zgartiradi.")
    libos = Libos.objects.select_for_update().get(id=libos.id, salon=salon)
    if libos.holat == Libos.Holat.TASDIQ_KUTILMOQDA:
        raise KatalogXatosi('Avval libosni tasdiqlang.')
    holat = maydonlar.pop('holat', None)
    for nom, qiymat in maydonlar.items():
        eski = getattr(libos, nom)
        if qiymat is not None and qiymat != eski:
            setattr(libos, nom, qiymat)
            if nom in ('ijara_narxi', 'tannarx', 'zalog'):
                jurnalga_yoz(salon, rahbar, f'{nom}_ozgardi', f'libos {libos.artikul}', eski, qiymat)
    if holat and holat != libos.holat:
        if holat not in QOLDA_HOLATLAR:
            raise KatalogXatosi("Bu holatga qo'lda o'tkazib bo'lmaydi.")
        if libos.tamirlar.filter(tugagan__isnull=True).exists():
            raise KatalogXatosi("Libosda tugallanmagan ta'mir bor: avval ta'mirni tugating.")
        from apps.bookings.models import Bron
        if holat != Libos.Holat.BOSH and Bron.kelgusi().filter(libos=libos).exists():
            # aks holda mijozning zakazi sotilgan/arxivdagi libosga bog'liq qolib ketardi
            raise KatalogXatosi("Libosning kelgusi bronlari bor: avval zakazlarni boshqa libosga o'tkazing yoki bekor qiling.")
        jurnalga_yoz(salon, rahbar, 'libos_holati', f'libos {libos.artikul}', libos.holat, holat)
        libos.holat = holat
    libos.save()
    return libos


# --- Aksessuarlar (4.4) ---

@transaction.atomic
def aksessuar_qoshish(*, salon, xodim, nomi, kod, kategoriya, ijara_narxi=0, tannarx=None, soni=1):
    """Aksessuar turini va uning donalarini qo'shadi. Sotuvchi tannarx kirita olmaydi; uning aksessuari
    rahbar tasdig'ini kutadi (libos kabi, FT-3.5, FT-3.6)."""
    if kategoriya.salon_id != salon.id or kategoriya.turi != kategoriya.Turi.AKSESSUAR:
        raise KatalogXatosi('Aksessuar kategoriyasi topilmadi.')
    rahbar = _rahbar(xodim)
    if not rahbar and not sozlama(salon).sotuvchi_libos_qoshadi:
        raise KatalogXatosi("Aksessuarni faqat rahbar qo'shadi (sozlamalarda belgilangan).")
    if not rahbar:
        tannarx = None
    kod = kod.strip().upper()
    try:
        with transaction.atomic():
            a = Aksessuar.objects.create(
                salon=salon, nomi=nomi.strip(), kod=kod, kategoriya=kategoriya, ijara_narxi=ijara_narxi,
                tannarx=tannarx, qoshgan=xodim,
                holat=(Aksessuar.Holat.FAOL if rahbar or not sozlama(salon).libos_tasdigi
                       else Aksessuar.Holat.TASDIQ_KUTILMOQDA))
    except IntegrityError:
        raise KatalogXatosi(f'«{kod}» kodi salonda allaqachon bor.')
    donalar_qoshish(salon=salon, aksessuar=a, soni=soni)
    jurnalga_yoz(salon, xodim, 'aksessuar_qoshildi', f'aksessuar {kod}', '',
                 f'{a.nomi}, {soni} dona, narx {ijara_narxi}, holat {a.holat}')
    return a


@transaction.atomic
def donalar_qoshish(*, salon, aksessuar, soni):
    """`soni` ta yangi dona; yorliqlar ketma-ket (FT-01, FT-02 ...), salon ichida noyob (FT-4.2)."""
    if not 1 <= soni <= 200:
        raise KatalogXatosi("Dona soni 1 dan 200 gacha bo'lishi kerak.")
    aksessuar = Aksessuar.objects.select_for_update().get(id=aksessuar.id, salon=salon)
    mavjud = aksessuar.donalar.count()
    yangi = [AksessuarDona(salon=salon, aksessuar=aksessuar, yorliq=f'{aksessuar.kod}-{mavjud + i:02d}')
             for i in range(1, soni + 1)]
    AksessuarDona.objects.bulk_create(yangi)
    return yangi


@transaction.atomic
def aksessuarni_tasdiqlash(*, salon, rahbar, aksessuar, ijara_narxi, tannarx):
    if not _rahbar(rahbar):
        raise KatalogXatosi('Aksessuarni faqat rahbar tasdiqlaydi.')
    a = Aksessuar.objects.select_for_update().get(id=aksessuar.id, salon=salon)
    if a.holat != Aksessuar.Holat.TASDIQ_KUTILMOQDA:
        raise KatalogXatosi('Aksessuar tasdiq kutmayapti.')
    a.ijara_narxi, a.tannarx, a.holat = ijara_narxi, tannarx, Aksessuar.Holat.FAOL
    a.save()
    jurnalga_yoz(salon, rahbar, 'aksessuar_tasdiqlandi', f'aksessuar {a.kod}', '',
                 f'narx {ijara_narxi}, tannarx {tannarx}')
    return a


@transaction.atomic
def aksessuarni_ozgartirish(*, salon, rahbar, aksessuar, **maydonlar):
    if not _rahbar(rahbar):
        raise KatalogXatosi("Narx va tannarxni faqat rahbar o'zgartiradi.")
    a = Aksessuar.objects.select_for_update().get(id=aksessuar.id, salon=salon)
    if a.holat == Aksessuar.Holat.TASDIQ_KUTILMOQDA:
        raise KatalogXatosi('Avval aksessuarni tasdiqlang.')
    if maydonlar.get('holat') == Aksessuar.Holat.ARXIV and a.holat != Aksessuar.Holat.ARXIV:
        from apps.bookings.models import AksessuarBron
        if AksessuarBron.kelgusi().filter(dona__aksessuar=a).exists():
            raise KatalogXatosi("Aksessuarning kelgusi bronlari bor: avval zakazlardan olib tashlang.")
    for nom, qiymat in maydonlar.items():
        eski = getattr(a, nom)
        if qiymat is not None and qiymat != eski:
            setattr(a, nom, qiymat)
            jurnalga_yoz(salon, rahbar, f'aksessuar_{nom}_ozgardi', f'aksessuar {a.kod}', eski, qiymat)
    a.save()
    return a
