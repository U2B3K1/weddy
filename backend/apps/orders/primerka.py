"""Primerka va «moslash» xizmati (FT-2.8). Ixtiyoriy: admin panelda yoqiladi."""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.tenants.models import sozlama

from .changes import OZGARTIRILADI, _log, _qayta_hisobla
from .models import Primerka, Zakaz


class PrimerkaXatosi(Exception):
    pass


def _zakaz(salon, zakaz):
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if zakaz.holat not in OZGARTIRILADI:
        raise PrimerkaXatosi('Primerka faqat libos berilmagan zakazga belgilanadi.')
    return zakaz


def _vaqtni_tekshir(zakaz, vaqt):
    kun = timezone.localtime(vaqt).date()
    if kun < timezone.localdate():
        raise PrimerkaXatosi("Primerkani o'tgan kunga belgilab bo'lmaydi.")
    if kun > zakaz.olib_ketish:
        raise PrimerkaXatosi("Primerka olib ketish kunidan kech bo'lishi mumkin emas.")


def _narxni_yangila(zakaz, xodim, eski):
    """Moslash narxi asosiy narxga qo'shiladi (FT-4.3: liboslar + aksessuarlar + qo'shimcha xizmatlar)."""
    zakaz.xizmatlar = (zakaz.primerkalar.exclude(holat=Primerka.Holat.BEKOR)
                       .aggregate(s=Sum('moslash_narxi'))['s'] or 0)
    if zakaz.xizmatlar == eski:
        return
    _qayta_hisobla(zakaz, PrimerkaXatosi)  # 6.1: qoldiq / to'liq to'langan / ortiqcha to'lov
    zakaz.save()
    _log(zakaz, xodim, 'moslash_narxi', eski, zakaz.xizmatlar)


@transaction.atomic
def primerka_belgilash(*, salon, xodim, zakaz, vaqt):
    if not sozlama(salon).primerka:
        raise PrimerkaXatosi("Primerka funksiyasi o'chirilgan (sozlamalarda yoqiladi).")
    zakaz = _zakaz(salon, zakaz)
    _vaqtni_tekshir(zakaz, vaqt)
    return Primerka.objects.create(salon=salon, zakaz=zakaz, vaqt=vaqt, xodim=xodim)


@transaction.atomic
def primerka_ozgartirish(*, salon, xodim, primerka, vaqt=None, natija=None, moslash_narxi=None, holat=None):
    """Vaqtni ko'chirish, natijani yozish, moslash narxini qo'shish yoki primerkani bekor qilish."""
    p = Primerka.objects.select_for_update().get(id=primerka.id, salon=salon)
    zakaz = _zakaz(salon, p.zakaz)
    eski = zakaz.xizmatlar
    if vaqt is not None and vaqt != p.vaqt:
        _vaqtni_tekshir(zakaz, vaqt)
        p.vaqt = vaqt
    if natija is not None:
        p.natija = natija
    if moslash_narxi is not None:
        p.moslash_narxi = moslash_narxi
    if holat is not None:
        if holat not in Primerka.Holat.values:
            raise PrimerkaXatosi("Holat noto'g'ri.")
        p.holat = holat
    p.save()
    _narxni_yangila(zakaz, xodim, eski)
    return p


def primerka_json(p):
    return {'id': p.id, 'zakaz': p.zakaz_id, 'vaqt': p.vaqt, 'natija': p.natija, 'moslash_narxi': p.moslash_narxi,
            'holat': p.holat}
