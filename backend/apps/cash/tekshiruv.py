"""Kunlik zalog tekshiruvi (FT-12.5) va yopilgan smenani tuzatish (FT-12.11)."""
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Zalog
from apps.tenants.models import Xodim, jurnalga_yoz

from .models import Smena, ZalogTekshiruvi
from .services import KassaXatosi, _faol_ishtirokchi

SAQLANADI = (Zalog.Holat.SAQLANMOQDA, Zalog.Holat.USHLAB_QOLINDI)


def _zaloglar(smena):
    """Salonda saqlanayotgan hujjat va tillo zaloglar. Filial kassasida — shu filial zakazlarining zaloglari."""
    qs = (Zalog.objects.filter(salon=smena.salon, holat__in=SAQLANADI).exclude(turi=Zalog.Turi.PUL)
          .select_related('zakaz__mijoz').order_by('yorliq', 'id'))
    return qs.filter(zakaz__filial_id=smena.filial_id) if smena.filial_id else qs


def zalog_royxati(smena):
    """[{zalog, ..., joyida: True/False/None}] — None: hali tekshirilmagan."""
    belgilar = dict(ZalogTekshiruvi.objects.filter(smena=smena).values_list('zalog_id', 'joyida'))
    natija = []
    for z in _zaloglar(smena):
        tavsif = f'{z.hujjat_turi} № {z.hujjat_raqami}' if z.turi == Zalog.Turi.HUJJAT else f'{z.tavsif}, {z.ogirlik_gr} g'
        natija.append({'id': z.id, 'yorliq': z.yorliq, 'turi': z.turi, 'tavsif': tavsif, 'zakaz_id': z.zakaz_id,
                       'zakaz_raqami': z.zakaz.raqam, 'mijoz': z.zakaz.mijoz.fio or z.zakaz.mijoz.telefon,
                       'joyida': belgilar.get(z.id)})
    return natija


def tekshirilmaganlar_soni(smena):
    belgilangan = set(ZalogTekshiruvi.objects.filter(smena=smena).values_list('zalog_id', flat=True))
    return sum(1 for z in _zaloglar(smena) if z.id not in belgilangan)


@transaction.atomic
def zalogni_belgilash(*, salon, xodim, smena, zalog, joyida, izoh=''):
    """Sotuvchi zalogni «joyida» yoki «yo'q» deb belgilaydi. «Yo'q» bo'lsa rahbarga darhol xabar ketadi."""
    if smena.yopilgan or not _faol_ishtirokchi(smena, xodim):
        raise KassaXatosi("Zaloglarni ochiq smenadagi sotuvchi tekshiradi.")
    if zalog.salon_id != salon.id or zalog.holat not in SAQLANADI or zalog.turi == Zalog.Turi.PUL:
        raise KassaXatosi('Bu zalog salonda saqlanmayapti.')
    if not joyida and not izoh.strip():
        raise KassaXatosi("Zalog joyida bo'lmasa izoh majburiy.")
    t, _ = ZalogTekshiruvi.objects.update_or_create(
        smena=smena, zalog=zalog, defaults={'salon': salon, 'joyida': joyida, 'izoh': izoh.strip(), 'xodim': xodim})
    if not joyida:
        from apps.notify.services import rahbarlarga
        rahbarlarga(salon, 'zalog_yoq',
                    f"Zalog joyida emas: {zalog.yorliq} ({zalog.get_turi_display()}), zakaz #{zalog.zakaz.raqam}.\n"
                    f"Belgiladi: {xodim.ism}. Izoh: {izoh.strip()}", kalit=f'zalog_yoq:{smena.id}:{zalog.id}')
    return t


@transaction.atomic
def smenani_tuzatish(*, salon, rahbar, smena, fakt_qoldiq=None, izoh=None):
    """Yopilgan smenani faqat rahbar o'zgartiradi (FT-12.11): fakt qoldiq va izoh; farq qayta hisoblanadi, jurnalga yoziladi."""
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise KassaXatosi("Yopilgan smenani faqat rahbar o'zgartiradi.")
    smena = Smena.objects.select_for_update().get(id=smena.id, salon=salon)
    if not smena.yopilgan:
        raise KassaXatosi('Smena hali ochiq: u odatdagi tartibda yopiladi.')
    eski = f'fakt {smena.fakt_qoldiq}, farq {smena.farq}'
    if fakt_qoldiq is not None:
        if fakt_qoldiq < 0:
            raise KassaXatosi("Qoldiq manfiy bo'lishi mumkin emas.")
        smena.fakt_qoldiq = fakt_qoldiq
        smena.farq = fakt_qoldiq - smena.hisobdagi_qoldiq
    if izoh is not None:
        smena.izoh = izoh
    if smena.farq != 0 and not (smena.izoh or '').strip():
        raise KassaXatosi('Kassa farqi bor: izoh majburiy.')
    smena.save(update_fields=['fakt_qoldiq', 'farq', 'izoh'])
    jurnalga_yoz(salon, rahbar, 'smena_tuzatildi', f'smena {smena.sana:%d.%m.%Y}', eski, f'fakt {smena.fakt_qoldiq}, farq {smena.farq}')
    return smena


def smena_json(s):
    return {'id': s.id, 'sana': s.sana, 'ochgan': s.ochgan.ism, 'filial': s.filial.nomi if s.filial_id else None,
            'boshlangich_qoldiq': s.boshlangich_qoldiq, 'hisobdagi_qoldiq': s.hisobdagi_qoldiq, 'fakt_qoldiq': s.fakt_qoldiq,
            'farq': s.farq, 'izoh': s.izoh, 'yopilgan': s.yopilgan,
            'zalog_tekshirilmagan': s.zalog_tekshirilmagan, 'zalog_yoq': s.zalog_yoq}


def yopishda_zalog_hisobi(smena):
    """Smena yopilayotganda zalog tekshiruvi natijasini smenaga yozadi; kamchilik bo'lsa rahbarga xabar matnini qaytaradi."""
    smena.zalog_tekshirilmagan = tekshirilmaganlar_soni(smena)
    smena.zalog_yoq = ZalogTekshiruvi.objects.filter(smena=smena, joyida=False).count()
    if smena.zalog_tekshirilmagan:
        return f"Smena {smena.sana:%d.%m.%Y} yopildi, lekin {smena.zalog_tekshirilmagan} ta hujjat/tillo zalog tekshirilmadi."
    return ''


__all__ = ['zalog_royxati', 'zalogni_belgilash', 'smenani_tuzatish', 'smena_json', 'yopishda_zalog_hisobi', 'timezone']
