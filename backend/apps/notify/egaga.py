"""Platforma egasiga Telegram orqali xizmat xabarlari: server xatolari va zaxira nusxa.

Ega botga platforma panelidan ulanadi (`PlatformaSozlama.telegram_chat_id`). Ulanmagan yoki bot sozlanmagan
bo'lsa hamma narsa jim o'tadi — bu modul hech qachon asosiy ishni (so'rov, cron) buzmasligi kerak.

Modul `settings.LOGGING` orqali Django ilovalari yuklanmasdan oldin import qilinadi, shuning uchun modellar
faqat funksiya ichida import qilinadi.
"""
import logging
import threading
import time
import traceback

XATO_TAKROR_SONIYA = 30 * 60   # bir xil xato shu vaqt ichida bir marta yoziladi
XATO_OYNA_SONIYA = 10 * 60     # ... va har qanday xatolar shu oynada ko'pi bilan XATO_OYNA_MAKS ta
XATO_OYNA_MAKS = 10
MANZIL_KESH_SONIYA = 5 * 60

_qulf = threading.Lock()
_oxirgi = {}        # xato kaliti → oxirgi yuborilgan vaqt
_oyna = []          # so'nggi yuborishlar vaqti
_manzil = (0, None)  # (olingan vaqt, (chat_id, token))


def ega_manzili(keshdan=False):
    """(chat_id, token) yoki None — ega ulanmagan / bot sozlanmagan.

    `keshdan=True`: xato ishlovchisi uchun — baza ishlamayotgan paytda ham (xatoning sababi shu bo'lishi mumkin)
    oxirgi ma'lum manzil ishlatiladi.
    """
    global _manzil
    hozir = time.monotonic()
    if keshdan and _manzil[1] and hozir - _manzil[0] < MANZIL_KESH_SONIYA:
        return _manzil[1]
    try:
        from apps.tenants.models import platforma_sozlama

        from . import telegram
        chat, token = platforma_sozlama().telegram_chat_id, telegram.token_ol()
    except Exception:  # noqa: BLE001 — baza yiqilgan yoki tranzaksiya buzilgan: oxirgi ma'lum manzil
        return _manzil[1] if keshdan else None
    manzil = (chat, token) if chat and token else None
    _manzil = (hozir, manzil)
    return manzil


def egaga_xabar(matn):
    """Egaga matn yuboradi. Yuborilsa True; ulanmagan bo'lsa yoki xato chiqsa False (istisno ko'tarilmaydi)."""
    from . import telegram
    manzil = ega_manzili()
    if not manzil:
        return False
    try:
        telegram.xabar_yubor(manzil[0], matn[:4000], token=manzil[1])
        return True
    except telegram.TelegramXatosi:
        return False


def egaga_fayl(nom, mazmun, izoh=''):
    """Egaga fayl yuboradi. Natija: 'yuborildi' | 'ulanmagan' | 'katta' | 'xato: ...'."""
    from . import telegram
    manzil = ega_manzili()
    if not manzil:
        return 'ulanmagan'
    if len(mazmun) > telegram.FAYL_MAKS_BAYT:
        return 'katta'
    try:
        telegram.fayl_yubor(manzil[0], nom, mazmun, izoh=izoh, token=manzil[1])
        return 'yuborildi'
    except telegram.TelegramXatosi as e:
        return f'xato: {e}'


def _ruxsat(kalit, hozir=None):
    """Takror va toshqindan himoya: shu xatoni hozir yuborish mumkinmi."""
    hozir = time.monotonic() if hozir is None else hozir
    with _qulf:
        if kalit in _oxirgi and hozir - _oxirgi[kalit] < XATO_TAKROR_SONIYA:
            return False
        _oyna[:] = [t for t in _oyna if hozir - t < XATO_OYNA_SONIYA]
        if len(_oyna) >= XATO_OYNA_MAKS:
            return False
        if len(_oxirgi) > 500:
            _oxirgi.clear()
        _oxirgi[kalit] = hozir
        _oyna.append(hozir)
        return True


def _joy(tb):
    """Xato chiqqan joy: iloji bo'lsa ilovaning o'z kodidagi eng ichki qator (`apps/...`)."""
    kadrlar = traceback.extract_tb(tb)
    oziniki = [k for k in kadrlar if '/apps/' in k.filename.replace('\\', '/')
               and 'site-packages' not in k.filename]
    k = (oziniki or kadrlar or [None])[-1]
    if not k:
        return ''
    yol = k.filename.replace('\\', '/')
    yol = yol[yol.rfind('/apps/') + 1:] if '/apps/' in yol else yol.rsplit('/', 1)[-1]
    return f'{yol}:{k.lineno} ({k.name})'


def xato_matni(record):
    """Log yozuvidan (kalit, matn). So'rov tanasi va sarlavhalari **qo'shilmaydi** — ularda PIN/parol bo'lishi mumkin."""
    qatorlar, joy, tur = [], '', ''
    sorov = getattr(record, 'request', None)
    metod, yol = getattr(sorov, 'method', ''), getattr(sorov, 'path', '')
    if metod and yol:
        qatorlar += [f"Server xatosi ({getattr(record, 'status_code', 500)})", f'{metod} {yol[:200]}']
    else:
        qatorlar += ['Ilova xatosi', f'{record.name}: {record.getMessage()[:300]}']
    if record.exc_info and record.exc_info[0]:
        tur = record.exc_info[0].__name__
        joy = _joy(record.exc_info[2])
        qatorlar.append(f'{tur}: {str(record.exc_info[1])[:300]}')
        if joy:
            qatorlar.append(f'Joyi: {joy}')
    kalit = f'{tur}|{joy}' if tur else f'{record.name}|{record.msg}'[:200]
    return kalit, '\n'.join(qatorlar)


class XatoXabarchi(logging.Handler):
    """ERROR darajasidagi loglarni (5xx javoblar, `log.exception`) platforma egasining Telegramiga yuboradi.

    So'rovni kechiktirmaslik uchun yuborish alohida oqimda; bir xil xato 30 daqiqada bir marta, jami 10 daqiqada
    10 tadan ko'p emas. `DEBUG` da va `XATO_XABARI=False` da o'chiq.
    """

    def emit(self, record):
        try:
            from django.conf import settings
            if not getattr(settings, 'XATO_XABARI', False):
                return
            kalit, matn = xato_matni(record)
            if not _ruxsat(kalit):
                return
            manzil = ega_manzili(keshdan=True)
            if not manzil:
                return
            threading.Thread(target=_yubor, args=(manzil, matn), daemon=True).start()
        except Exception:  # noqa: BLE001 — log ishlovchisi hech qachon ilovani yiqitmasin
            pass


def _yubor(manzil, matn):
    try:
        from . import telegram
        telegram.xabar_yubor(manzil[0], matn[:4000], token=manzil[1])
    except Exception:  # noqa: BLE001 — Telegram ishlamasa xabar yo'qoladi; log baribir journald da
        pass
