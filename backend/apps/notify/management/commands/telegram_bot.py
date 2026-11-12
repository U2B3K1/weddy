import time

from django.core.management.base import BaseCommand, CommandError

from apps.notify import bot_menyu, telegram, vidjet
from apps.tenants.models import platforma_sozlama
from apps.notify.services import (korsat_tugma_ishla, kutayotganlarni_yubor, qurilma_start_ishla, start_ishla,
                                  start_ishla_platforma, tugma_ishla)


def _javob_yubor(chat_id, javob, tugmalar, tk):
    """`tugmalar` ro'yxat bo'lsa — inline tugmalar; lug'at bo'lsa — tayyor reply_markup (masalan, force_reply)."""
    if isinstance(tugmalar, dict) and 'vidjet' in tugmalar:
        try:
            vidjet.yubor(chat_id, javob, tugmalar['vidjet'], tk.get('token'))
        except telegram.TelegramXatosi:  # server vidjetni qabul qilmadi — matnning o'zi ketadi
            telegram.xabar_yubor(chat_id, javob, **tk)
        return
    if isinstance(tugmalar, dict):
        telegram.xabar_yubor(chat_id, javob, klaviatura=tugmalar, **tk)
        return
    try:
        telegram.xabar_yubor(chat_id, javob, tugmalar, **tk)
    except telegram.TelegramXatosi:
        # «nusxa olish» tugmasini eski Telegram serveri/ilovasi tanimasa — xabar usiz baribir yetib borsin
        oddiy = [q for q in ([t for t in qator if 'copy_text' not in t] for qator in (tugmalar or [])) if q]
        if oddiy == (tugmalar or []):
            raise
        telegram.xabar_yubor(chat_id, javob, oddiy or None, **tk)


def yangilanishni_ishla(u, token=None):
    """Bitta Telegram yangilanishi: `/start <kod>`, menyu tugmasi, erkin matn (zakaz qidiruvi) yoki inline tugma.

    Oxirgi javob matnini qaytaradi (test uchun).
    """
    tk = {'token': token} if token else {}
    if 'message' in u:
        m = u['message']
        matn = (m.get('text') or '').strip()
        chat_id = m['chat']['id']
        if m['chat'].get('type') != 'private':
            return None  # guruhlarda ishlamaydi: xabarlarda mijoz ma'lumoti bor
        javobga = (m.get('reply_to_message') or {}).get('text') or ''
        if m.get('photo') or m.get('document'):  # rasm/fayl: faqat rahbarning to'lov cheki
            javob = None
            for javob, tugmalar in bot_menyu.chek_ishla(chat_id, m, javobga):
                _javob_yubor(chat_id, javob, tugmalar, tk)
            return javob
        kod = matn[6:].strip() if matn.startswith('/start') else ''
        if kod.startswith('q_'):  # yangi qurilmani tasdiqlash havolasi
            javob, tugmalar = qurilma_start_ishla(chat_id, kod[2:])
            telegram.xabar_yubor(chat_id, javob, tugmalar, **tk)
            return javob
        if kod:  # ulash kodi: platforma egasi yoki xodim; ulangach pastki menyu chiqadi
            javob = start_ishla_platforma(chat_id, kod)
            if javob is None:
                javob = start_ishla(chat_id, kod)
            telegram.xabar_yubor(chat_id, javob, klaviatura=bot_menyu.klaviatura(chat_id), **tk)
            return javob
        if matn in ('/start', '/menu', '/menyu'):
            kl = bot_menyu.klaviatura(chat_id)
            javob = ("Pastdagi menyudan tanlang. Zakazni topish uchun raqamini yoki mijoz telefonini yozing." if kl
                     else "Libosa boti. Ulash uchun ilovada «Telegramni ulash» tugmasini bosing.")
            telegram.xabar_yubor(chat_id, javob, klaviatura=kl, **tk)
            return javob
        javob = None
        for javob, tugmalar in bot_menyu.matn_ishla(chat_id, matn, javobga):
            _javob_yubor(chat_id, javob, tugmalar, tk)
        return javob
    if 'widget_query' in u:  # vidjetdagi «Yangilash»
        return vidjet.sorov_ishla(u['widget_query'], token)
    if 'callback_query' in u:
        c = u['callback_query']
        kw = {'_token': token} if token else {}
        data = c.get('data') or ''
        if data.startswith(('m:', 'e:', 'tc:')):  # menyu, ega tugmasi, chek so'rovi — javob yangi xabar bo'lib keladi
            telegram.api('answerCallbackQuery', callback_query_id=c['id'], **kw)
            javob = None
            ishlovchi = {'m': bot_menyu.tugma_ishla, 'e': bot_menyu.ega_tugma, 'tc': bot_menyu.chek_tugma}[data.split(':')[0]]
            for javob, tugmalar in ishlovchi(c['from']['id'], data):
                _javob_yubor(c['from']['id'], javob, tugmalar, tk)
            return javob
        if data.startswith(('s:', 'k:')):  # sozlamalar va yashirin xabarni ochish: o'sha xabarning o'zi yangilanadi
            if data.startswith('s:'):
                javob, matn, tugmalar = bot_menyu.sozlama_tugma(c['from']['id'], data)
            else:
                javob, matn, tugmalar = korsat_tugma_ishla(c['from']['id'], data[2:] if data[2:].isdigit() else 0)
            telegram.api('answerCallbackQuery', callback_query_id=c['id'], text=javob[:190], **kw)
            if matn and c.get('message'):
                telegram.api('editMessageText', chat_id=c['message']['chat']['id'], message_id=c['message']['message_id'],
                             text=matn, **({'reply_markup': {'inline_keyboard': tugmalar}} if tugmalar else {}), **kw)
            return javob or matn
        javob = tugma_ishla(c['from']['id'], data)
        telegram.api('answerCallbackQuery', callback_query_id=c['id'], text=javob[:190], **kw)
        if c.get('message'):  # tugmalarni olib tashlab, natijani yozib qo'yadi (ikki marta bosilmasligi uchun)
            xabar = c['message']
            manzil = {'chat_id': xabar['chat']['id'], 'message_id': xabar['message_id']}
            if 'text' in xabar or 'caption' not in xabar:
                telegram.api('editMessageText', text=f"{xabar.get('text', '')}\n\n— {javob}", **manzil, **kw)
            else:  # rasm yoki fayl (to'lov cheki): matni — izohda
                telegram.api('editMessageCaption', caption=f"{xabar['caption']}\n\n— {javob}"[:1024], **manzil, **kw)
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
        vidjetsiz_gacha = 0.0  # `widget_query` ni so'rash xato bergan bo'lsa — shu vaqtgacha so'ralmaydi
        tekshirilgan = 0.0  # nazorat eslatmalari daqiqada ko'pi bilan bir marta
        while True:
            try:
                token = (telegram.barcha_tokenlar() or [None])[0]
                if not token:
                    time.sleep(15)
                    continue
                if time.monotonic() - tekshirilgan >= 60:
                    tekshirilgan = time.monotonic()
                    try:
                        from apps.cash.nazorat import tezkor_eslatmalar
                        from apps.notify.management.commands.eslatmalarni_yuborish import primerka_eslatmalari
                        from apps.notify import yurak
                        yurak.ur('bot')
                        yurak.nazorat('bot')  # cron to'xtab qolgan bo'lsa — egaga
                        tezkor_eslatmalar()
                        primerka_eslatmalari()
                    except Exception as e:  # noqa: BLE001 — eslatma xatosi botni to'xtatmasin
                        self.stderr.write(f'Nazorat eslatmalarida xato: {type(e).__name__}')
                try:
                    kutayotganlarni_yubor()
                except Exception as e:  # noqa: BLE001 — navbatdagi xato tinglashni to'xtatmasin
                    self.stderr.write(f'Navbatni yuborishda xato: {type(e).__name__}')
                # Vidjet so'rovlari faqat vidjet yoqilganda so'raladi: yangi tur tufayli getUpdates rad etilsa,
                # bot butunlay to'xtab qolmasligi uchun bir soat usiz ishlaydi
                turlar = ['message', 'callback_query']
                vidjetli = platforma_sozlama().bot_vidjet and time.monotonic() >= vidjetsiz_gacha
                try:
                    yangilanishlar = telegram.api('getUpdates', _token=token, offset=offset, timeout=25,
                                                  allowed_updates=turlar + (['widget_query'] if vidjetli else []))
                except telegram.TelegramXatosi as e:
                    self.stderr.write(f'Telegram xatosi: {e}')
                    if vidjetli and 'Timeout' not in str(e):
                        vidjetsiz_gacha = time.monotonic() + 3600
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
