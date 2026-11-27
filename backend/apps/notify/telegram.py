"""Telegram Bot API bilan ishlash. Tashqi kutubxonasiz (oddiy HTTPS so'rov): test qilish va almashtirish oson.

Bitta bot butun platformaga xizmat qiladi (FT-4.14): token `PlatformaSozlama` dan olinadi, bo'lmasa `.env`
(`settings.TELEGRAM_BOT_TOKEN`). Salonlar o'z botini yuritmaydi — shu sababli `salon` argumenti saqlanib qoldi
(chaqiruv joylari o'zgarmasin), lekin **e'tiborga olinmaydi**.

Eslatma: TZ 7.1 da aiogram tavsiya etilgan. Bitta bot uchun `getUpdates` (long poll) yetarli —
`telegram_bot` buyrug'i shu asosda ishlaydi.
"""
import http.client
import json
import socket
import ssl
import urllib.error
import urllib.request
import uuid

from django.conf import settings

TIMEOUT = 5
ULANISH_TIMEOUT = 2  # soniya: bitta manzilga TCP ulanish uchun; osilsa — keyingi manzil (IPv4 → IPv6)
# Tugma javobi va xabarni tahrirlash: takrorlansa zarar yo'q (ikkinchi marta — «message is not modified» yoki
# «query is too old», bular jimgina o'tkaziladi). Telegram odatda 0,1 s da javob beradi — osilgan so'rov qisqa
# kutiladi va bir marta qayta yuboriladi. `sendMessage` takrorlanmaydi: xabar ikki marta borib qolishi mumkin.
TAKRORLANADIGAN = {'answerCallbackQuery', 'editMessageText', 'editMessageCaption', 'editMessageReplyMarkup'}
TEZ_TIMEOUT = 3


def _ulan(address, timeout=None, source_address=None):
    """TCP ulanish (`socket.create_connection` o'rnida): avval IPv4, har manzilga `ULANISH_TIMEOUT` soniya.

    2026-11-26: serverdan api.telegram.org ga ulanish ba'zan osilib qolardi (bir urinish 12 s, keyingisi 0,1 s;
    bot tugmasi 5,1 s kutgan). Oddiy `urlopen` manzillarni tartib bilan, har biriga to'liq muddat berib sinaydi —
    osilgan manzil butun so'rovni ushlab turardi va bot o'sha paytda boshqa tugmalarga javob bermasdi.
    `timeout` berilmagan so'rovda (urllib maxsus belgi uzatadi) — ulanishdan keyin cheklovsiz.
    """
    host, port = address
    timeout = timeout if isinstance(timeout, (int, float)) else None
    manzillar = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    manzillar.sort(key=lambda m: m[0] != socket.AF_INET)  # barqaror saralash: IPv4 lar birinchi, tartibi saqlanadi
    xato = None
    for oila, tur, proto, _, manzil in manzillar:
        s = socket.socket(oila, tur, proto)
        s.settimeout(min(ULANISH_TIMEOUT, timeout) if timeout else ULANISH_TIMEOUT)
        try:
            if source_address:
                s.bind(source_address)
            s.connect(manzil)
        except OSError as e:
            s.close()
            xato = e
            continue
        s.settimeout(timeout)
        return s
    raise xato or OSError(f'{host}: manzil topilmadi')


class _Ulanish(http.client.HTTPSConnection):
    """Faqat TCP ulanish usuli almashtiriladi: TLS, TCP_NODELAY va proksi tunneli — standart kodda qoladi."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _ulan


class _Ishlovchi(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_Ulanish, req, context=self._context)


# `urllib.request.urlopen` shu ochuvchidan foydalanadi (testlar `urlopen` ni almashtirib qo'yadi — tarmoqqa chiqilmaydi).
# Loyihadagi boshqa HTTPS so'rovlariga (SMS) ham ta'siri faqat shu: IPv4 birinchi, osilgan manzil qisqa kutiladi.
urllib.request.install_opener(urllib.request.build_opener(_Ishlovchi(context=ssl.create_default_context())))


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


class TelegramTarmoqXatosi(TelegramXatosi):
    """Vaqtinchalik: tarmoq uzildi, javob kelmadi yoki Telegram serverida xato (5xx).

    Xabar navbatda qoladi va keyinroq qayta yuboriladi. Ilgari bunday xato «XATO» deb belgilanardi va qayta
    yuborilmasdi — bir lahzalik uzilish zakaz arxividagi xabarni butunlay yo'qotardi.
    """


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
    if metod not in TAKRORLANADIGAN:
        return _chaqir(req, params.get('timeout', 0) + TIMEOUT)
    try:
        return _chaqir(req, TEZ_TIMEOUT)
    except TelegramTarmoqXatosi:  # osilgan yoki uzilgan ulanish — yangisi bilan bir marta
        return _chaqir(req, TEZ_TIMEOUT)


def _chaqir(req, timeout):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
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
        if e.code >= 500:
            raise TelegramTarmoqXatosi(f'HTTP {e.code} {tavsif}'.strip())
        raise TelegramXatosi(f'HTTP {e.code} {tavsif}'.strip())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise TelegramTarmoqXatosi(type(e).__name__)  # token URL ichida — xato matniga chiqarilmaydi
    if not javob.get('ok'):
        raise TelegramXatosi(str(javob.get('description', 'xato'))[:200])
    return javob.get('result')


def xabar_yubor(chat_id, matn, tugmalar=None, token=None, klaviatura=None, jim=False):
    """`tugmalar` — xabar ostidagi inline tugmalar; `klaviatura` — pastki doimiy menyu (reply keyboard);
    `jim` — ovozsiz (telefon jiringlamaydi): arxiv uchun yoziladigan xabarlar."""
    params = {'chat_id': chat_id, 'text': matn}
    if tugmalar:
        params['reply_markup'] = {'inline_keyboard': tugmalar}
    elif klaviatura:
        params['reply_markup'] = klaviatura
    if jim:
        params['disable_notification'] = True
    if token:
        params['_token'] = token
    return api('sendMessage', **params)


def tekshir(token):
    """Tokenni tekshiradi (getMe) va bot nomini qaytaradi: {'username': ...}. Yaroqsiz bo'lsa TelegramXatosi."""
    j = api('getMe', _token=token)
    return {'username': (j or {}).get('username', '')}


FAYL_MAKS_BAYT = 49 * 1024 * 1024  # Bot API fayl chegarasi 50 MB — biroz zaxira bilan
FAYL_TIMEOUT = 120


def fayl_ol(file_id, maks, token=None):
    """Foydalanuvchi yuborgan fayl (ovozli xabar, rasm) baytlari: `getFile` + yuklab olish. `maks` dan katta — xato."""
    token = token or token_ol()
    f = api('getFile', _token=token, file_id=file_id) or {}
    if not f.get('file_path') or (f.get('file_size') or 0) > maks:
        raise TelegramXatosi('Fayl topilmadi yoki juda katta.')
    req = urllib.request.Request(f"https://api.telegram.org/file/bot{token}/{f['file_path']}")
    try:
        with urllib.request.urlopen(req, timeout=FAYL_TIMEOUT) as r:
            mazmun = r.read(maks + 1)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise TelegramXatosi(type(e).__name__)  # token URL ichida — xato matniga chiqarilmaydi
    if len(mazmun) > maks:
        raise TelegramXatosi('Fayl juda katta.')
    return mazmun


def fayl_yubor(chat_id, nom, mazmun, izoh='', token=None):
    """Chatga fayl yuboradi (`sendDocument`, multipart). `mazmun` — bayt; `FAYL_MAKS_BAYT` dan oshmasligi kerak."""
    token = token or token_ol()
    if not token:
        raise TelegramXatosi('Telegram bot sozlanmagan.')
    if len(mazmun) > FAYL_MAKS_BAYT:
        raise TelegramXatosi('Fayl Telegram chegarasidan katta.')
    chegara = '----libosa' + uuid.uuid4().hex
    xavfsiz_nom = ''.join(c for c in nom if c.isalnum() or c in '-_.') or 'fayl'
    qismlar = []
    for kalit, qiymat in (('chat_id', str(chat_id)), ('caption', izoh[:1000])):
        if qiymat:
            qismlar.append(f'--{chegara}\r\nContent-Disposition: form-data; name="{kalit}"\r\n\r\n{qiymat}\r\n'.encode())
    qismlar.append((f'--{chegara}\r\nContent-Disposition: form-data; name="document"; filename="{xavfsiz_nom}"\r\n'
                    'Content-Type: application/octet-stream\r\n\r\n').encode())
    tana = b''.join(qismlar) + mazmun + f'\r\n--{chegara}--\r\n'.encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendDocument', data=tana,
                                 headers={'Content-Type': f'multipart/form-data; boundary={chegara}'})
    try:
        with urllib.request.urlopen(req, timeout=FAYL_TIMEOUT) as r:
            javob = json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            tavsif = str(json.loads(e.read()).get('description', '')).strip()
        except Exception:  # noqa: BLE001 — javob JSON bo'lmasligi mumkin
            tavsif = ''
        raise TelegramXatosi(f'HTTP {e.code} {tavsif}'.strip())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise TelegramXatosi(type(e).__name__)  # token URL ichida — xato matniga chiqarilmaydi
    if not javob.get('ok'):
        raise TelegramXatosi(str(javob.get('description', 'xato'))[:200])
    return javob.get('result')
