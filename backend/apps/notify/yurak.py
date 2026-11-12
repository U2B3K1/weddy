"""Yurak urishi: fon vazifalari (cron) va bot jarayoni oxirgi marta qachon ishlagani.

Har vazifa ishlaganda `ur(nom)` chaqiradi. Bot va soatlik cron bir-birini kuzatadi (`nazorat`): biri to'xtab qolsa,
ikkinchisi platforma egasiga yozadi — egaga xabar Telegram API orqali to'g'ridan-to'g'ri ketadi, bot jarayoni shart emas.
Ikkalasi ham to'xtasa — `/api/sogliq/` 503 qaytaradi va tashqi monitoring ogohlantiradi (deploy/DEPLOY.md).
"""
import logging
from datetime import timedelta

from django.utils import timezone

from .models import Yurak

log = logging.getLogger(__name__)

# nom → (ko'rinadigan nom, shuncha daqiqa urmasa «to'xtagan» hisoblanadi)
VAZIFALAR = {
    'bot': ('Bot jarayoni', 5),
    'bron': ('Bronlarni tozalash', 30),      # cron: har 10 daqiqada
    'kunlik': ('Kunlik hisobot', 45),        # cron: har 15 daqiqada
    'eslatma': ('Eslatmalar', 150),          # cron: har soatda
}
QAYTA_OGOHLANTIRISH = timedelta(hours=6)


def ur(nom):
    """Vazifa ishladi. Avval «to'xtagan» deb ogohlantirilgan bo'lsa — egaga «yana ishlayapti» deb yozadi."""
    try:
        y, _ = Yurak.objects.get_or_create(nom=nom, defaults={'vaqt': timezone.now()})
        tiklandi = bool(y.ogohlantirildi)
        y.vaqt, y.ogohlantirildi = timezone.now(), None
        y.save(update_fields=['vaqt', 'ogohlantirildi'])
        if tiklandi:
            from .egaga import egaga_xabar
            egaga_xabar(f"✅ {VAZIFALAR[nom][0]} yana ishlayapti.")
    except Exception:  # noqa: BLE001 — kuzatuv asosiy ishni hech qachon to'xtatmasin
        log.exception('Yurak urishini yozib bo\'lmadi')


def holatlar(hozir=None):
    """[(nom, ko'rinadigan nom, oxirgi vaqt yoki None, to'xtaganmi)] — hali bir marta ham ishlamagan vazifa baholanmaydi."""
    hozir = hozir or timezone.now()
    bor = {y.nom: y for y in Yurak.objects.all()}
    return [(nom, sarlavha, bor[nom].vaqt if nom in bor else None,
             nom in bor and bor[nom].vaqt < hozir - timedelta(minutes=daqiqa))
            for nom, (sarlavha, daqiqa) in VAZIFALAR.items()]


def toxtaganlar(hozir=None):
    return [h for h in holatlar(hozir) if h[3]]


def nazorat(oz_nomi, hozir=None):
    """To'xtab qolgan boshqa vazifalar haqida egaga yozadi (har biri uchun 6 soatda ko'pi bilan bir marta)."""
    hozir = hozir or timezone.now()
    soni = 0
    try:
        from .egaga import egaga_xabar
        for nom, sarlavha, vaqt, _ in toxtaganlar(hozir):
            y = Yurak.objects.get(nom=nom)
            if nom == oz_nomi or (y.ogohlantirildi and y.ogohlantirildi > hozir - QAYTA_OGOHLANTIRISH):
                continue
            daqiqa = int((hozir - vaqt).total_seconds() // 60)
            qancha = f'{daqiqa} daqiqadan' if daqiqa < 120 else f'{daqiqa // 60} soatdan'
            if egaga_xabar(f"⚠️ {sarlavha} {qancha} beri ishlamayapti (oxirgi marta {timezone.localtime(vaqt):%d.%m %H:%M}).\n"
                           "Serverni tekshiring."):
                Yurak.objects.filter(nom=nom).update(ogohlantirildi=hozir)
                soni += 1
    except Exception:  # noqa: BLE001
        log.exception('Yurak nazoratida xato')
    return soni
