"""Server sog'lig'i: monitoring (yoki nginx/uptime xizmati) server tirik va bazaga ulanganini tekshiradi.

Tokensiz, hech qanday ma'lumot qaytarmaydi — faqat holat. Baza ishlamasa yoki fon vazifasi (cron, bot jarayoni)
to'xtab qolgan bo'lsa 503: monitoring ogohlantirsin. Hali bir marta ham ishlamagan vazifa hisobga olinmaydi.
"""
import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

log = logging.getLogger(__name__)


@require_GET
def sogliq(request):
    try:
        connection.ensure_connection()
        baza = True
    except Exception:  # bazaga ulanib bo'lmadi — sababi logga, javobda tafsilot yo'q
        log.exception("Sog'liq tekshiruvi: bazaga ulanib bo'lmadi")
        baza = False
    fon = True
    if baza:
        try:
            from apps.notify.yurak import toxtaganlar
            fon = not toxtaganlar()
        except Exception:  # jadval hali yo'q (migratsiyadan oldin) — bazaning o'zi ishlayapti
            log.exception("Sog'liq tekshiruvi: fon vazifalari holatini o'qib bo'lmadi")
    javob = {'holat': 'ok' if baza and fon else 'xato', 'baza': baza}
    if not fon:
        javob['fon'] = False
    return JsonResponse(javob, status=200 if baza and fon else 503)
