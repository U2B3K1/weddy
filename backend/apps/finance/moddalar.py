"""Xarajat moddalari (FT-13.1) va doimiy oylik xarajatlar (FT-13.3).

Standart moddalar kodda (`Xarajat.Modda`); rahbar qo'shgan moddalar `XarajatModdasi` da va `Xarajat.modda` ichida
`m<id>` kodi bilan saqlanadi.
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import DoimiyXarajat, Xarajat, XarajatModdasi


def _kod(m):
    return f'm{m.id}'


def moddalar(salon, faqat_faol=True):
    """[{kod, nomi, togridan, standart, faol}] — standart moddalar va salonning o'z moddalari."""
    natija = [{'kod': k, 'nomi': nom, 'togridan': k in Xarajat.TOGRIDAN_TOGRI, 'standart': True, 'faol': True}
              for k, nom in Xarajat.Modda.choices]
    qs = XarajatModdasi.objects.filter(salon=salon)
    if faqat_faol:
        qs = qs.filter(faol=True)
    natija += [{'kod': _kod(m), 'id': m.id, 'nomi': m.nomi, 'togridan': m.togridan, 'standart': False, 'faol': m.faol} for m in qs]
    return natija


def modda_nomlari(salon):
    """{kod: nom} — arxivlangan moddalar bilan (eski xarajatlar nomi yo'qolmasligi uchun)."""
    return {m['kod']: m['nomi'] for m in moddalar(salon, faqat_faol=False)}


def modda_bormi(salon, kod, faqat_faol=True):
    return any(m['kod'] == kod for m in moddalar(salon, faqat_faol))


def togridan_kodlar(salon):
    """To'g'ridan-to'g'ri xarajat (P&L 2-qator) moddalari kodlari."""
    return list(Xarajat.TOGRIDAN_TOGRI) + [_kod(m) for m in XarajatModdasi.objects.filter(salon=salon, togridan=True)]


@transaction.atomic
def doimiy_qoralamalarni_yarat(salon, bugun=None):
    """Har bir faol doimiy xarajat uchun joriy oyga bitta qoralama (tasdiq kutayotgan xarajat) yaratadi.

    Oy davomida istalgan marta chaqirilsa ham har shablondan oyiga bitta yoziladi. Rahbar uni tasdiqlaydi, summani
    o'zgartirib tasdiqlaydi yoki rad etadi — tasdiqlanmaguncha foyda/zarar hisobotiga kirmaydi.
    """
    bugun = bugun or timezone.localdate()
    oy = f'{bugun.year}-{bugun.month:02d}'
    soni = 0
    for d in DoimiyXarajat.objects.filter(salon=salon, faol=True):
        if not modda_bormi(salon, d.modda, faqat_faol=False):
            continue
        try:
            with transaction.atomic():
                Xarajat.objects.create(salon=salon, sana=bugun.replace(day=1), modda=d.modda, summa=d.summa, usul='karta',
                                       izoh=(d.izoh or 'Doimiy oylik xarajat')[:300], holat=Xarajat.Holat.KUTILMOQDA,
                                       doimiy=d, doimiy_oy=oy, filial=d.filial)
            soni += 1
        except IntegrityError:
            continue  # shu oyga allaqachon yaratilgan
    return soni
