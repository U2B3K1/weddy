import logging
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone

from apps.notify import bot_menyu, telegram, vidjet, yordam
from apps.tenants.models import platforma_sozlama
from apps.notify.services import (korsat_tugma_ishla, kutayotganlarni_yubor, qurilma_start_ishla, start_ishla,
                                  start_ishla_platforma, tugma_ishla)

log = logging.getLogger(__name__)
# Telegramdagi «Menu» tugmasi ro'yxati (setMyCommands): qo'llab-quvvatlash pastki menyuda emas — kam ishlatiladi
BUYRUQLAR = [{'command': 'menyu', 'description': 'Menyuni ochish'},
             {'command': 'yordam', 'description': "Qo'llab-quvvatlash: savol yoki muammo yozish"}]
NAVBAT_MUDDATI = 8  # soniya: navbatdagi xabarlarni yuborish bir aylanishda shundan oshmaydi (tugmalar kutib qolmasin)
SEKIN = 3  # soniya: bundan uzoq ishlagan yangilanish jurnalga yoziladi
# getUpdates kutish muddati (long poll). 25 s edi: javobi yo'qolgan so'rov (serverdan Telegramga ulanish ba'zan
# osilib qoladi — jurnalda «Telegram xatosi: TimeoutError») botni 30 s «kar» qilardi, shu payt bosilgan tugma
# javobsiz qolardi. 10 s da eng yomon holat — 15 s; so'rovlar soni daqiqasiga 6 ta (Telegram uchun arzimas).
UZUN_SOROV = 10


def _javob_yubor(chat_id, javob, tugmalar, tk):
    """`tugmalar` ro'yxat bo'lsa — inline tugmalar; lug'at bo'lsa — tayyor reply_markup (masalan, force_reply)."""
    if isinstance(tugmalar, dict) and 'vidjet' in tugmalar:
        try:
            vidjet.yubor(chat_id, javob, tugmalar['vidjet'], tk.get('token'))
        except telegram.TelegramXatosi:  # server vidjetni qabul qilmadi — matn o'zining oddiy tugmalari bilan ketadi
            _javob_yubor(chat_id, javob, tugmalar.get('zaxira'), tk)
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
        # Qo'llab-quvvatlash — boshqa ishlovlardan oldin: ega javobi chek, qidiruv yoki to'lov ma'lumotiga tushmasin,
        # rejimdagi foydalanuvchi xabari esa zakaz qidiruviga emas, egaga ketsin
        if m.get('reply_to_message') and bot_menyu.egami(chat_id) and yordam.ega_javobi(chat_id, m, token):
            return 'yordam:javob'
        buyruq = matn.split()[0].split('@')[0].lower() if matn.startswith('/') else ''
        kod = matn[6:].strip() if buyruq == '/start' else ''
        if buyruq == '/yordam' or kod == 'yordam' or kod.startswith('y_'):
            javob = None
            for javob, tugmalar in yordam.boshlash(chat_id, yordam.havola_xodimi(kod) if kod.startswith('y_') else None):
                _javob_yubor(chat_id, javob, tugmalar, tk)
            return javob
        if buyruq == '/bekor':
            javob = ("💬 Qo'llab-quvvatlash yozish rejimi tugadi." if yordam.tugat(chat_id)
                     else "Bekor qilinadigan narsa yo'q.")
            telegram.xabar_yubor(chat_id, javob, klaviatura=bot_menyu.klaviatura(chat_id), **tk)
            return javob
        if (r := yordam.rejim(chat_id)):
            muddati_otgan = r.tugaydi <= timezone.now()
            # Menyu tugmasi, buyruq, chek so'roviga javob yoki zakaz qidiruviga o'xshash matn (raqam, telefon,
            # «A12 25.11») — rejimdan chiqadi va odatdagidek ishlanadi: mijoz ma'lumoti egaga ketib qolmasin
            if (buyruq or bot_menyu.menyu_tugmasimi(matn) or javobga.startswith(bot_menyu.CHEK_SORAV)
                    or bot_menyu.qidiruv_shaklimi(matn)):
                yordam.tugat(chat_id)
                if not muddati_otgan:
                    telegram.xabar_yubor(chat_id, "💬 Qo'llab-quvvatlash yozish rejimi tugadi.", **tk)
            elif muddati_otgan:  # jimlikdan keyin yozilgan matn yoki fayl — egaga ham, qidiruvga ham ketmaydi
                yordam.tugat(chat_id)
                javob = ("💬 Qo'llab-quvvatlash yozish rejimi 30 daqiqa jimlikdan keyin tugadi — bu xabar yuborilmadi. "
                         "Yana yozish uchun: /yordam.")
                telegram.xabar_yubor(chat_id, javob, klaviatura=bot_menyu.klaviatura(chat_id), **tk)
                return javob
            else:
                javob = None
                for javob, tugmalar in yordam.murojaat_qabul(chat_id, m, token):
                    _javob_yubor(chat_id, javob, tugmalar, tk)
                return javob or 'yordam:yuborildi'
        if m.get('photo') or m.get('document'):  # rasm/fayl: faqat rahbarning to'lov cheki
            javob = None
            for javob, tugmalar in bot_menyu.chek_ishla(chat_id, m, javobga):
                _javob_yubor(chat_id, javob, tugmalar, tk)
            return javob
        if not matn and yordam.xabar_turi(m) not in (None, 'matn'):  # ovozli xabar, stiker… — faqat qo'llab-quvvatlashda
            javob = "Ovozli xabar va boshqa fayllarni qo'llab-quvvatlashga yuborish uchun avval /yordam ni bosing."
            telegram.xabar_yubor(chat_id, javob, **tk)
            return javob
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
            javob = (bot_menyu.START_MATNI if kl
                     else "Libosa boti. Ulash uchun ilovada «Telegramni ulash» tugmasini bosing.\n"
                          "Savol yoki muammo bo'lsa — /yordam (qo'llab-quvvatlash).")
            telegram.xabar_yubor(chat_id, javob, klaviatura=kl, **tk)
            return javob
        javob = None
        kl = bot_menyu.klaviatura(chat_id)  # tugmasiz javob bilan joriy menyu ham ketadi: telefondagi eski menyu yangilanadi
        for javob, tugmalar in bot_menyu.matn_ishla(chat_id, matn, javobga):
            _javob_yubor(chat_id, javob, tugmalar if tugmalar is not None else kl, tk)
        return javob
    if 'widget_query' in u:  # vidjetdagi «Yangilash»
        return vidjet.sorov_ishla(u['widget_query'], token)
    if 'callback_query' in u:
        c = u['callback_query']
        kw = {'_token': token} if token else {}
        data = c.get('data') or ''
        if data.startswith(('m:', 'e:', 'tc:', 'yd:')):  # menyu, ega tugmasi, chek, qo'llab-quvvatlash — yangi xabar
            _tinchgina('answerCallbackQuery', callback_query_id=c['id'], **kw)
            javob = None
            ishlovchi = {'m': bot_menyu.tugma_ishla, 'e': bot_menyu.ega_tugma, 'tc': bot_menyu.chek_tugma,
                         'yd': lambda chat, _data: yordam.boshlash(chat)}[data.split(':')[0]]
            for javob, tugmalar in ishlovchi(c['from']['id'], data):
                _javob_yubor(c['from']['id'], javob, tugmalar, tk)
            return javob
        if data.startswith(('s:', 'k:', 'b:')):  # sozlamalar, yashirin xabar, «Bugun» yangilash: o'sha xabar yangilanadi
            if data.startswith('s:'):
                javob, matn, tugmalar = bot_menyu.sozlama_tugma(c['from']['id'], data)
            elif data.startswith('b:'):
                javob, matn, tugmalar = bot_menyu.bugun_tugma(c['from']['id'], data)
            else:
                javob, matn, tugmalar = korsat_tugma_ishla(c['from']['id'], data[2:] if data[2:].isdigit() else 0)
            _tinchgina('answerCallbackQuery', callback_query_id=c['id'], text=javob[:190], **kw)
            if matn and c.get('message'):
                _tinchgina('editMessageText', chat_id=c['message']['chat']['id'], message_id=c['message']['message_id'],
                           text=matn, **({'reply_markup': {'inline_keyboard': tugmalar}} if tugmalar else {}), **kw)
            return javob or matn
        javob = tugma_ishla(c['from']['id'], data)
        _tinchgina('answerCallbackQuery', callback_query_id=c['id'], text=javob[:190], **kw)
        if c.get('message'):  # tugmalarni olib tashlab, natijani yozib qo'yadi (ikki marta bosilmasligi uchun)
            xabar = c['message']
            manzil = {'chat_id': xabar['chat']['id'], 'message_id': xabar['message_id']}
            if 'text' in xabar or 'caption' not in xabar:
                _tinchgina('editMessageText', text=f"{xabar.get('text', '')}\n\n— {javob}", **manzil, **kw)
            else:  # rasm yoki fayl (to'lov cheki): matni — izohda
                _tinchgina('editMessageCaption', caption=f"{xabar['caption']}\n\n— {javob}"[:1024], **manzil, **kw)
        return javob
    return None


def _tinchgina(metod, **params):
    """Tugma javobi va xabarni tahrirlash. Xato amalni to'xtatmasin: bot band bo'lib qolganda tugma 15 soniyadan
    eskiradi («query is too old»), bir xil tanlov qayta bosilsa — «message is not modified». Ilgari shu xato
    butun javobni tashlab yuborardi va foydalanuvchi uchun bot «qotib» qolardi."""
    try:
        return telegram.api(metod, **params)
    except telegram.TelegramXatosi as e:
        log.warning('%s bajarilmadi: %s', metod, e)
        return None


def _tur(u):
    """Jurnal uchun yangilanish turi (matn yoki shaxsiy ma'lumotsiz): «xabar», «tugma:m» va h.k."""
    if 'callback_query' in u:
        return 'tugma:' + ((u['callback_query'].get('data') or '').split(':')[0] or '?')
    return 'xabar' if 'message' in u else next(iter(u.keys() - {'update_id'}), '?')


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
        buyruqlar_qoyildi = None  # Telegram menyusidagi buyruqlar shu token uchun qo'yilgan
        while True:
            try:
                # Uzoq yashaydigan jarayon: baza ulanishi uzilgan bo'lsa (Postgres qayta yoqilgan va h.k.) — yangisi
                # ochiladi. Aks holda har so'rov xato berib, bot qayta ishga tushirilguncha «qotib» turardi.
                close_old_connections()
                token = (telegram.barcha_tokenlar() or [None])[0]
                if not token:
                    time.sleep(15)
                    continue
                if buyruqlar_qoyildi != token:  # bir marta (token almashsa — qayta); xato botni to'xtatmaydi
                    buyruqlar_qoyildi = token
                    if not _tinchgina('setMyCommands', _token=token, commands=BUYRUQLAR):
                        self.stderr.write('Telegram menyusiga buyruqlarni qo\'yib bo\'lmadi')
                oraliq = time.monotonic()  # eslatma va navbat ishi: shu payt tugmalar kutib turadi
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
                    kutayotganlarni_yubor(muddat=NAVBAT_MUDDATI)
                except Exception as e:  # noqa: BLE001 — navbatdagi xato tinglashni to'xtatmasin
                    self.stderr.write(f'Navbatni yuborishda xato: {type(e).__name__}: {str(e)[:150]}')
                if (sarf := time.monotonic() - oraliq) >= SEKIN:
                    self.stderr.write(f'Sekin aylanish (eslatma/navbat): {sarf:.1f} s')
                # Vidjet so'rovlari faqat vidjet yoqilganda so'raladi: yangi tur tufayli getUpdates rad etilsa,
                # bot butunlay to'xtab qolmasligi uchun bir soat usiz ishlaydi
                turlar = ['message', 'callback_query']
                vidjetli = platforma_sozlama().bot_vidjet and time.monotonic() >= vidjetsiz_gacha
                try:
                    yangilanishlar = telegram.api('getUpdates', _token=token, offset=offset, timeout=UZUN_SOROV,
                                                  allowed_updates=turlar + (['widget_query'] if vidjetli else []))
                except telegram.TelegramXatosi as e:
                    self.stderr.write(f'Telegram xatosi: {e}')
                    if vidjetli and 'Timeout' not in str(e):
                        vidjetsiz_gacha = time.monotonic() + 3600
                    time.sleep(1)
                    continue
                for u in yangilanishlar:
                    offset = u['update_id'] + 1
                    boshlandi = time.monotonic()
                    try:
                        yangilanishni_ishla(u, token)
                    except Exception as e:  # noqa: BLE001 — bitta yomon yangilanish botni to'xtatmasin
                        self.stderr.write(f'Yangilanishda xato ({_tur(u)}): {type(e).__name__}: {str(e)[:150]}')
                    sarf = time.monotonic() - boshlandi
                    if sarf >= SEKIN:
                        self.stderr.write(f'Sekin javob ({_tur(u)}): {sarf:.1f} s')
            except KeyboardInterrupt:
                break
            except Exception as e:  # noqa: BLE001 — baza yoki tarmoq uzilishi: biroz kutib, qaytadan
                self.stderr.write(f'Aylanishda xato: {type(e).__name__}: {str(e)[:150]}')
                time.sleep(3)
