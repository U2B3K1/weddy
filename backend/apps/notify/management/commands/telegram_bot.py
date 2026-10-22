import time

from django.core.management.base import BaseCommand, CommandError

from apps.notify import telegram
from apps.notify.services import (kutayotganlarni_yubor, qurilma_start_ishla, start_ishla, start_ishla_platforma,
                                  tugma_ishla)


def yangilanishni_ishla(u, token=None):
    """Bitta Telegram yangilanishi: `/start <kod>` yoki inline tugma. Javob matnini qaytaradi (test uchun)."""
    if 'message' in u:
        m = u['message']
        matn = (m.get('text') or '').strip()
        chat_id = m['chat']['id']
        if m['chat'].get('type') != 'private':
            return None  # guruhlarda ishlamaydi: xabarlarda mijoz ma'lumoti bor
        tugmalar = None
        kod = matn[6:].strip()
        if matn.startswith('/start') and kod.startswith('q_'):  # yangi qurilmani tasdiqlash havolasi
            javob, tugmalar = qurilma_start_ishla(chat_id, kod[2:])
        elif matn.startswith('/start'):
            javob = start_ishla_platforma(chat_id, kod)
            if javob is None:
                javob = start_ishla(chat_id, kod)
        else:
            javob = "Libosa boti. Ulash uchun ilovada «Telegramni ulash» tugmasini bosing."
        telegram.xabar_yubor(chat_id, javob, tugmalar, **({'token': token} if token else {}))
        return javob
    if 'callback_query' in u:
        c = u['callback_query']
        javob = tugma_ishla(c['from']['id'], c.get('data'))
        kw = {'_token': token} if token else {}
        telegram.api('answerCallbackQuery', callback_query_id=c['id'], text=javob[:190], **kw)
        if c.get('message'):  # tugmalarni olib tashlab, natijani yozib qo'yadi (ikki marta bosilmasligi uchun)
            telegram.api('editMessageText', chat_id=c['message']['chat']['id'], message_id=c['message']['message_id'],
                         text=f"{c['message'].get('text', '')}\n\n— {javob}", **kw)
        return javob
    return None


class Command(BaseCommand):
    help = "Telegram botni ishga tushiradi (long polling): xodimni ulash va chegirma tugmalari."

    def handle(self, *args, **opts):
        """Platforma botini tinglaydi (bitta bot, bitta jarayon — ikkinchisi ishga tushsa Telegram 409 beradi).

        Token har aylanishda qayta o'qiladi: platforma egasi panelda tokenni almashtirsa, buyruqni
        qayta ishga tushirish shart emas.
        """
        if not telegram.barcha_tokenlar():
            self.stdout.write("Hozircha bot sozlanmagan (platforma paneli yoki .env). Kutilmoqda…")
        self.stdout.write("Telegram bot ishga tushdi. To'xtatish: Ctrl+C")
        offset = 0
        while True:
            try:
                token = (telegram.barcha_tokenlar() or [None])[0]
                if not token:
                    time.sleep(15)
                    continue
                try:
                    kutayotganlarni_yubor()
                except Exception as e:  # noqa: BLE001 — navbatdagi xato tinglashni to'xtatmasin
                    self.stderr.write(f'Navbatni yuborishda xato: {type(e).__name__}')
                try:
                    yangilanishlar = telegram.api('getUpdates', _token=token, offset=offset, timeout=25,
                                                  allowed_updates=['message', 'callback_query'])
                except telegram.TelegramXatosi as e:
                    self.stderr.write(f'Telegram xatosi: {e}')
                    time.sleep(1)
                    continue
                for u in yangilanishlar:
                    offset = u['update_id'] + 1
                    try:
                        yangilanishni_ishla(u, token)
                    except Exception as e:  # noqa: BLE001 — bitta yomon yangilanish botni to'xtatmasin
                        self.stderr.write(f'Yangilanishda xato: {type(e).__name__}')
            except KeyboardInterrupt:
                break
