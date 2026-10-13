"""Aksessuar donalari uchun ta'mir jurnali (FT-3.10 ning aksessuarlarga tatbiqi)."""
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.finance.services import xarajat_kiritish
from apps.tenants.models import jurnalga_yoz

from .models import AksessuarDona, DonaTamiri
from .services import KatalogXatosi


@transaction.atomic
def donani_tamirga_berish(*, salon, xodim, dona, ish_turi, kim=''):
    """Dona «Ta'mirda» holatiga o'tadi va yangi zakazlarga berilmaydi. Kelgusi bronlari bor dona ta'mirga berilmaydi."""
    from apps.bookings.models import AksessuarBron

    if not ish_turi.strip():
        raise KatalogXatosi('Nima qilinishini yozing.')
    dona = AksessuarDona.objects.select_for_update().get(id=dona.id, salon=salon)
    if dona.holat != AksessuarDona.Holat.BOSH:
        raise KatalogXatosi(f'Dona hozir «{dona.get_holat_display()}» holatida, ta\'mirga berib bo\'lmaydi.')
    if AksessuarBron.faol().filter(dona=dona).exists():
        raise KatalogXatosi("Bu donada bronlar bor; avval bronlarni boshqa donaga o'tkazing.")
    try:
        with transaction.atomic():
            yozuv = DonaTamiri.objects.create(salon=salon, dona=dona, ish_turi=ish_turi.strip(), kim=kim.strip(),
                                              boshlangan=timezone.localdate(), kiritgan=xodim)
    except IntegrityError:
        raise KatalogXatosi("Bu donada tugallanmagan ta'mir bor.")
    dona.holat = AksessuarDona.Holat.TAMIRDA
    dona.save(update_fields=['holat'])
    jurnalga_yoz(salon, xodim, 'tamirga_berildi', f'dona {dona.yorliq}', 'bosh', ish_turi.strip())
    return yozuv


@transaction.atomic
def dona_tamirini_tugatish(*, salon, xodim, yozuv, narx=0, kassadan=None, usul='naqd'):
    """Ta'mir tugadi: dona yana bo'sh, narx «ta'mirlash» xarajatiga tushadi (P&L 2-qator)."""
    yozuv = DonaTamiri.objects.select_for_update().select_related('dona__aksessuar').get(id=yozuv.id, salon=salon)
    if yozuv.tugagan:
        raise KatalogXatosi("Bu ta'mir allaqachon tugatilgan.")
    if narx < 0:
        raise KatalogXatosi("Narx manfiy bo'lishi mumkin emas.")
    bugun = timezone.localdate()
    yozuv.tugagan, yozuv.narx, yozuv.tugatgan = bugun, narx, xodim
    if narx > 0:
        yozuv.xarajat = xarajat_kiritish(
            salon=salon, xodim=xodim, modda='tamir', summa=narx, sana=bugun, usul=usul, kassadan=kassadan,
            izoh=f'{yozuv.dona.aksessuar.nomi} ({yozuv.dona.yorliq}): {yozuv.ish_turi}'[:300])
    yozuv.save()
    dona = AksessuarDona.objects.select_for_update().get(id=yozuv.dona_id)
    if dona.holat == AksessuarDona.Holat.TAMIRDA:  # rahbar holatni qo'lda o'zgartirgan bo'lsa tegilmaydi
        dona.holat = AksessuarDona.Holat.BOSH
        dona.save(update_fields=['holat'])
    jurnalga_yoz(salon, xodim, 'tamir_tugadi', f'dona {dona.yorliq}', '', f'{yozuv.ish_turi}, narx {narx}')
    return yozuv


def dona_tamir_json(t):
    return {'id': t.id, 'dona': t.dona_id, 'ish_turi': t.ish_turi, 'kim': t.kim, 'boshlangan': t.boshlangan,
            'tugagan': t.tugagan, 'narx': t.narx,
            'kunlar': ((t.tugagan or timezone.localdate()) - t.boshlangan).days,
            'xarajat_holati': t.xarajat.holat if t.xarajat_id else None}
