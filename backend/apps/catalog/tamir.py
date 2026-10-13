"""Ta'mir va moslash jurnali (FT-3.10)."""
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.finance.services import xarajat_kiritish
from apps.tenants.models import jurnalga_yoz

from .models import Libos, TamirYozuvi
from .services import KatalogXatosi


@transaction.atomic
def tamirga_berish(*, salon, xodim, libos, ish_turi, kim='', sana=None):
    """Libosni «Ta'mirda» holatiga o'tkazadi: shu paytdan boshlab yangi zakazlarda ko'rinmaydi (FT-2.3).

    Mijozda turgan libosni ta'mirga berib bo'lmaydi. Kelgusi bronlar saqlanadi — ularga ulgurish rahbar zimmasida.
    """
    from apps.orders.models import Zakaz  # orders katalogga bog'liq, shu sabab ichkarida import

    if not ish_turi.strip():
        raise KatalogXatosi('Nima qilinishini yozing.')
    libos = Libos.objects.select_for_update().get(id=libos.id, salon=salon)
    if libos.holat not in (Libos.Holat.BOSH, Libos.Holat.TOZALASHDA):
        raise KatalogXatosi(f'Libos hozir «{libos.get_holat_display()}» holatida, ta\'mirga berib bo\'lmaydi.')
    if Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.BERILDI, pozitsiyalar__libos=libos).exists():
        raise KatalogXatosi('Libos hozir mijozda.')
    sana = sana or timezone.localdate()
    if sana > timezone.localdate():
        raise KatalogXatosi("Kelajakdagi sanani kiritib bo'lmaydi.")
    try:
        with transaction.atomic():
            yozuv = TamirYozuvi.objects.create(salon=salon, libos=libos, ish_turi=ish_turi.strip(),
                                               kim=kim.strip(), boshlangan=sana, kiritgan=xodim)
    except IntegrityError:
        raise KatalogXatosi("Bu libosda tugallanmagan ta'mir bor.")
    eski = libos.holat
    libos.holat = Libos.Holat.TAMIRDA
    libos.save(update_fields=['holat'])
    jurnalga_yoz(salon, xodim, 'tamirga_berildi', f'libos {libos.artikul}', eski, ish_turi.strip())
    return yozuv


@transaction.atomic
def tamirni_tugatish(*, salon, xodim, yozuv, narx=0, sana=None, kassadan=None, usul='naqd'):
    """Ta'mir tugadi: libos yana bo'sh, narx to'g'ridan-to'g'ri xarajatga tushadi (FT-3.10, P&L 2-qator).

    Sotuvchi kiritgan narx kassadan chiqim bo'ladi va rahbar tasdig'ini kutadi; rahbarniki darhol tasdiqlangan.
    """
    yozuv = TamirYozuvi.objects.select_for_update().select_related('libos').get(id=yozuv.id, salon=salon)
    if yozuv.tugagan:
        raise KatalogXatosi("Bu ta'mir allaqachon tugatilgan.")
    if narx < 0:
        raise KatalogXatosi("Narx manfiy bo'lishi mumkin emas.")
    sana = sana or timezone.localdate()
    if sana < yozuv.boshlangan or sana > timezone.localdate():
        raise KatalogXatosi("Tugash sanasi boshlanishdan oldin yoki kelajakda bo'lishi mumkin emas.")
    yozuv.tugagan, yozuv.narx, yozuv.tugatgan = sana, narx, xodim
    if narx > 0:
        yozuv.xarajat = xarajat_kiritish(
            salon=salon, xodim=xodim, modda='tamir', summa=narx, sana=sana, usul=usul, kassadan=kassadan,
            izoh=f'{yozuv.libos.artikul}: {yozuv.ish_turi}'[:300])
    yozuv.save()
    libos = Libos.objects.select_for_update().get(id=yozuv.libos_id)
    if libos.holat == Libos.Holat.TAMIRDA:  # rahbar holatni qo'lda o'zgartirgan bo'lsa tegilmaydi
        libos.holat = Libos.Holat.BOSH
        libos.save(update_fields=['holat'])
    jurnalga_yoz(salon, xodim, 'tamir_tugadi', f'libos {libos.artikul}', '',
                 f'{yozuv.ish_turi}, {yozuv.kunlar()} kun, narx {narx}')
    return yozuv
