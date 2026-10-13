"""Telegram Bot API bilan ishlash. Tashqi kutubxonasiz (oddiy HTTPS so'rov): test qilish va almashtirish oson.

Bitta bot butun platformaga xizmat qiladi (FT-4.14): token `PlatformaSozlama` dan olinadi, bo'lmasa `.env`
(`settings.TELEGRAM_BOT_TOKEN`). Salonlar o'z botini yuritmaydi — shu sababli `salon` argumenti saqlanib qoldi
(chaqiruv joylari o'zgarmasin), lekin **e'tiborga olinmaydi**.

Eslatma: TZ 7.1 da aiogram tavsiya etilgan. Bitta bot uchun `getUpdates` (25 s long poll) yetarli —
`telegram_bot` buyrug'i shu asosda ishlaydi.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings

TIMEOUT = 5


class TelegramXatosi(Exception):
    pass


class TelegramLimitXatosi(TelegramXatosi):
    """429 — juda ko'p so'rov yuborildi.

    Bitta bot butun platformaga xizmat qilgani uchun limit umumiy: kunlik hisobot 21:00 da hamma salonga
    birdan ketadi. Bunday xato **vaqtinchalik** — xabar navbatda qolib, keyingi aylanishda qayta yuboriladi
    (XATO deb belgilansa, u butunlay yo'qolar edi).
    """

    def __init__(self, xabar, kuting=1):
        super().__init__(xabar)
        self.kuting = max(1, int(kuting or 1))


def token_ol(salon=None):
    """Platforma bot tokeni: avval panel orqali kiritilgani, bo'lmasa `.env`; ikkalasi ham bo'sh bo'lsa ''."""
    from apps.tenants.models import platforma_sozlama
    t = platforma_sozlama().telegram_token
    return t or settings.TELEGRAM_BOT_TOKEN


def bot_nomi(salon=None):
    """Botning @nomi (ulash havolasi uchun): avval panel, bo'lmasa `.env`."""
    from apps.tenants.models import platforma_sozlama
    return platforma_sozlama().telegram_bot_nomi or settings.TELEGRAM_BOT_NAME


def barcha_tokenlar():
    """Bot buyrug'i tinglashi kerak bo'lgan tokenlar: endi har doim bitta (platforma boti)."""
    t = token_ol()
    return [t] if t else []


def sozlangan(salon=None):
    return bool(token_ol(salon))


def api(metod, _token=None, **params):
    """Bot API metodini chaqiradi va `result` ni qaytaradi. `_token` berilmasa platforma boti ishlatiladi."""
    token = _token or token_ol()
    if not token:
        raise TelegramXatosi('Telegram bot sozlanmagan.')
    url = f'https://api.telegram.org/bot{token}/{metod}'
    req = urllib.request.Request(url, data=json.dumps(params).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=params.get('timeout', 0) + TIMEOUT) as r:
            javob = json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            xato = json.loads(e.read())
        except Exception:  # noqa: BLE001 — javob JSON bo'lmasligi mumkin
            xato = {}
        tavsif = str(xato.get('description', '')).strip()
        if e.code == 429:
            raise TelegramLimitXatosi(f'HTTP 429 {tavsif}'.strip(),
                                     kuting=(xato.get('parameters') or {}).get('retry_after', 1))
        raise TelegramXatosi(f'HTTP {e.code} {tavsif}'.strip())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise TelegramXatosi(type(e).__name__)  # token URL ichida — xato matniga chiqarilmaydi
    if not javob.get('ok'):
        raise TelegramXatosi(str(javob.get('description', 'xato'))[:200])
    return javob.get('result')


def xabar_yubor(chat_id, matn, tugmalar=None, token=None):
    params = {'chat_id': chat_id, 'text': matn}
    if tugmalar:
        params['reply_markup'] = {'inline_keyboard': tugmalar}
    if token:
        params['_token'] = token
    return api('sendMessage', **params)


def tekshir(token):
    """Tokenni tekshiradi (getMe) va bot nomini qaytaradi: {'username': ...}. Yaroqsiz bo'lsa TelegramXatosi."""
    j = api('getMe', _token=token)
    return {'username': (j or {}).get('username', '')}
