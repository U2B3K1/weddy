"""Server sog'lig'i: monitoring (yoki nginx/uptime xizmati) server tirik va bazaga ulanganini tekshiradi.

Tokensiz, hech qanday ma'lumot qaytarmaydi — faqat holat. Baza ishlamasa 503: monitoring ogohlantirsin.
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
    return JsonResponse({'holat': 'ok' if baza else 'xato', 'baza': baza}, status=200 if baza else 503)
