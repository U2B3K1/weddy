"""Qo'llab-quvvatlash: botdagi foydalanuvchi ↔ platforma egasi, bot orqali (alohida bot yoki tiket tizimisiz).

Foydalanuvchi /yordam (Telegram menyusidagi buyruq, «⚙️ Sozlamalar» dagi tugma yoki ilovadagi «Qo'llab-quvvatlash»
havolasi) bilan «yozish rejimi»ga o'tadi. Rejimdagi har xabari (matn, rasm, ovoz, fayl…) egaga nusxa bo'lib boradi,
sarlavhada kim yozgani. Ega Telegramda shu xabarga «reply» qilib javob yozadi — javob foydalanuvchiga uning
xabariga javob bo'lib boradi.

Qoidalar:
- Javob qaysi chatga ketishi faqat `Murojaat` qatoridan olinadi (ega chati + undagi xabar raqami). Qatori yo'q
  murojaat xabariga javob — egaga «yetkazilmadi» deyiladi va hech qachon boshqa ishlovga (zakaz qidiruviga) tushmaydi.
- Foydalanuvchiga «yuborildi» faqat uzatish muvaffaqiyatli bo'lib, qator saqlangach aytiladi.
- Rejim menyu tugmasi, buyruq yoki 30 daqiqa jimlikdan keyin ko'rinadigan qilib tugaydi: zakaz qidiruvidagi mijoz
  ismi va telefoni tasodifan egaga ketmasin. Rejim bazada — bot qayta ishga tushsa ham yo'qolmaydi.
- /yordam ni istalgan odam yozishi mumkin: Telegram ismi «tasdiqlanmagan» deb ko'rsatiladi; chegaralar — bitta
  chatdan sutkasiga 30 ta, hammasidan 300 ta xabar (ega chatiga nazorat va to'lov xabarlari ham keladi).
"""
import base64
import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.tenants.models import Salon, Xodim, platforma_sozlama

from . import telegram
from .models import Murojaat, YordamMavzu, YordamRejimi

REJIM_MUDDATI = timedelta(minutes=30)
CHAT_KUNLIK_MAKS = 30
JAMI_KUNLIK_MAKS = 300
# Message.caption faqat shu turlarda bo'ladi (Bot API) — boshqalariga izoh berilmaydi, sarlavha alohida xabar
IZOHLI_TURLAR = ('photo', 'animation', 'video', 'document', 'audio', 'voice')
TURLAR = {'matn': 'matn', 'photo': 'rasm', 'animation': 'GIF', 'video': 'video', 'document': 'fayl', 'audio': 'audio',
          'voice': 'ovozli xabar', 'video_note': 'dumaloq video', 'sticker': 'stiker', 'location': 'joylashuv',
          'contact': 'kontakt'}
SARLAVHA = "💬 Murojaat"
JAVOB_SARLAVHASI = "💬 Libosa qo'llab-quvvatlash"
SAVOL_MATNI = ("💬 Qo'llab-quvvatlash\nSavolingiz yoki muammoingizni yozing — matn, skrinshot yoki ovozli xabar. "
               "Platforma egasi shu chatda javob beradi.\n\nTugatish: /bekor yoki menyudagi istalgan tugma.")
ISHLAMAYDI = "Qo'llab-quvvatlash hozircha ishlamayapti. Birozdan keyin urinib ko'ring."


# ---------- ilovadagi havola ----------

def _imzo(xodim_id):
    raqam = hmac.new(settings.SECRET_KEY.encode(), f'yordam:{xodim_id}'.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raqam[:9]).decode()  # 12 belgi: Telegram start parametriga mos (A-Z a-z 0-9 - _)


def havola(xodim):
    """Ilovadagi «Qo'llab-quvvatlash» uchun: `https://t.me/<bot>?start=y_<xodim>_<imzo>`.

    Bot yoki ega ulanmagan bo'lsa (u hech kimga ishlamasdi) va o'quv salonida (xabar tashqariga chiqmaydi) — None.
    Havola xodimni Telegramga ulamaydi va hech qanday ruxsat bermaydi — faqat egaga «kim yozayotgani» ko'rinadi.
    """
    from .egaga import ega_manzili
    nomi = (telegram.bot_nomi() or '').lstrip('@')
    if not nomi or not ega_manzili() or xodim.salon.oquv:
        return None
    return f'https://t.me/{nomi}?start=y_{xodim.id}_{_imzo(xodim.id)}'


def havola_xodimi(kod):
    """`y_<xodim>_<imzo>` → havolani yaratgan xodim (imzo to'g'ri bo'lsa), aks holda None."""
    q = (kod or '').split('_', 2)  # imzoning o'zida «_» bo'lishi mumkin
    if len(q) != 3 or q[0] != 'y' or not q[1].isdigit() or not hmac.compare_digest(q[2], _imzo(int(q[1]))):
        return None
    return Xodim.objects.select_related('salon').filter(id=int(q[1]), faol=True, salon__oquv=False).first()


# ---------- yozish rejimi ----------

def boshlash(chat_id, xodim=None):
    """«Qo'llab-quvvatlashga yozish» rejimini yoqadi: [(matn, tugmalar)]."""
    from .bot_menyu import egami
    from .egaga import ega_manzili
    if egami(chat_id):
        return [("Siz platforma egasisiz: murojaatlar shu chatga keladi. Javob berish — murojaat xabariga «reply» qiling.",
                 None)]
    if not ega_manzili():
        return [(ISHLAMAYDI, None)]
    rejim, yangi = YordamRejimi.objects.get_or_create(
        chat_id=chat_id, defaults={'xodim': xodim, 'tugaydi': timezone.now() + REJIM_MUDDATI})
    if not yangi:
        rejim.tugaydi = timezone.now() + REJIM_MUDDATI
        if xodim:  # oddiy /yordam ilova havolasidan kelgan «kim»ni o'chirmaydi
            rejim.xodim = xodim
        rejim.save(update_fields=['tugaydi', 'xodim'])
    return [(SAVOL_MATNI, None)]


def rejim(chat_id):
    """Chatning rejim qatori (muddati o'tgan bo'lsa ham) yoki None."""
    return YordamRejimi.objects.select_related('xodim__salon').filter(chat_id=chat_id).first()


def tugat(chat_id):
    return YordamRejimi.objects.filter(chat_id=chat_id).delete()[0] > 0


# ---------- foydalanuvchi → ega ----------

def xabar_turi(m):
    if m.get('text'):
        return 'matn'
    return next((k for k in TURLAR if k != 'matn' and m.get(k)), None)  # animation — document dan oldin


def _salon_holati(s):
    return '' if s.holat == Salon.Holat.FAOL else f" · salon: {s.get_holat_display().lower()}"


def _kim(chat_id, profil, r):
    """Egaga ko'rsatiladigan yozuv va (xodim, salon). Telegram ulangan xodim — ishonchli (bloklangan salonniki ham:
    unga yordam ayniqsa kerak); ilova havolasi — «havolani yaratgan»; aks holda Telegram profili — tasdiqlanmagan."""
    ulangan = list(Xodim.objects.filter(telegram_id=chat_id, faol=True, salon__oquv=False)
                   .select_related('salon').order_by('salon__nomi'))
    if ulangan:
        return ('\n'.join(f"{x.salon.nomi} · {x.ism} ({x.get_rol_display()}){_salon_holati(x.salon)}" for x in ulangan),
                ulangan[0], ulangan[0].salon)
    ism = ' '.join(filter(None, [profil.get('first_name'), profil.get('last_name')])).strip() or 'ismsiz'
    if profil.get('username'):
        ism += f" (@{profil['username']})"
    if r and r.xodim_id:
        x = r.xodim
        return (f"{x.salon.nomi} · {x.ism} ({x.get_rol_display()}){_salon_holati(x.salon)} — ilovadagi havoladan;\n"
                f"Telegram: {ism}, botga ulanmagan"), x, x.salon
    return f"Telegram: {ism} — salonga ulanmagan, tasdiqlanmagan", None, None


def guruh():
    """Qo'llab-quvvatlash guruhi (mavzuli) — ulangan bo'lsa id, aks holda None."""
    from apps.tenants.models import platforma_sozlama
    return platforma_sozlama().yordam_guruh_id


def _mavzu(chat_id, guruh_id, nom, token, yangi=False):
    """Murojaatchining guruhdagi mavzusi (message_thread_id); yo'q bo'lsa (yoki `yangi`) — ochiladi."""
    q = YordamMavzu.objects.filter(guruh_id=guruh_id, chat_id=chat_id).first()
    if q and not yangi:
        return q.mavzu_id
    mavzu = telegram.api('createForumTopic', _token=token, chat_id=guruh_id, name=nom[:128] or 'Murojaat')['message_thread_id']
    YordamMavzu.objects.update_or_create(guruh_id=guruh_id, chat_id=chat_id, defaults={'mavzu_id': mavzu})
    return mavzu


def _uzat(chat_id, m, tur, sarlavha, tugma, kw):
    """Foydalanuvchi xabarini egaga (shaxsiy chat yoki guruh mavzusi) ko'chiradi → (xabar id, alohida sarlavha id)."""
    if tur == 'matn':
        return telegram.api('sendMessage', text=f"{sarlavha}\n\n{m['text']}"[:4096], **tugma, **kw)['message_id'], None
    izoh = (m.get('caption') or '').strip()
    try:
        if tur not in IZOHLI_TURLAR:
            raise telegram.TelegramXatosi('izohsiz tur')
        return telegram.api('copyMessage', from_chat_id=chat_id, message_id=m['message_id'],
                            caption=(sarlavha + (f"\n\n{izoh}" if izoh else ''))[:1024], **tugma, **kw)['message_id'], None
    except (telegram.TelegramTarmoqXatosi, telegram.TelegramLimitXatosi):  # vaqtinchalik — boshqa yo'l bilan urinmaydi
        raise
    except telegram.TelegramXatosi as e:  # izohsiz tur yoki izoh rad etildi — sarlavha alohida, nusxa izohsiz
        if 'thread' in str(e).lower():
            raise
        sarlavha_id = telegram.api('sendMessage', text=f"{sarlavha}\n({TURLAR[tur]})", **tugma, **kw)['message_id']
        return telegram.api('copyMessage', from_chat_id=chat_id, message_id=m['message_id'], **kw)['message_id'], sarlavha_id


def murojaat_qabul(chat_id, m, token=None):
    """Rejimdagi foydalanuvchi xabari egaga uzatiladi. Foydalanuvchiga javoblar: [(matn, None)]."""
    from .egaga import ega_manzili
    hozir = timezone.now()
    manzil = ega_manzili()
    if not manzil:
        return [(ISHLAMAYDI, None)]
    sutka = hozir - timedelta(days=1)
    if (Murojaat.objects.filter(chat_id=chat_id, yaratilgan__gt=sutka).count() >= CHAT_KUNLIK_MAKS
            or Murojaat.objects.filter(yaratilgan__gt=sutka).count() >= JAMI_KUNLIK_MAKS):
        return [("Bugun juda ko'p xabar yuborildi. Ertaga yozing yoki javobni kuting.", None)]
    tur = xabar_turi(m)
    if not tur:
        return [("Bu turdagi xabarni yuborib bo'lmaydi. Matn, rasm, fayl yoki ovozli xabar yuboring.", None)]
    r = rejim(chat_id)
    kim, xodim, salon = _kim(chat_id, m.get('from') or {}, r)
    ega_chat, ega_token = manzil
    kw = {'_token': ega_token, 'chat_id': ega_chat}
    guruh_id = guruh()
    sarlavha = f"{SARLAVHA} · {kim}\n↩️ Javob berish: shu xabarga «reply» qiling."
    if guruh_id:  # mavzuli guruh: har murojaatchiga alohida mavzu, javob — mavzu ichida oddiy yoziladi
        try:
            kw = {'_token': ega_token, 'chat_id': guruh_id,
                  'message_thread_id': _mavzu(chat_id, guruh_id, kim.split('\n')[0], ega_token)}
            ega_chat = guruh_id
            sarlavha = f"{SARLAVHA} · {kim}"
        except telegram.TelegramXatosi:  # guruh o'chirilgan, bot admin emas va h.k. — eganing shaxsiy chatiga
            pass
    # Ega murojaatdan salonga o'tadi (obuna, rahbar, to'lov kiritish); salon noma'lum bo'lsa — salonlar ro'yxati
    tugma = {'reply_markup': {'inline_keyboard': [[
        {'text': f'🏪 {salon.nomi[:40]}', 'callback_data': f'e:s:{salon.id}'} if salon else
        {'text': '🏪 Salonlar', 'callback_data': 'e:sl'}]]}}
    if 'message_thread_id' in kw:  # ega «hal bo'ldi» deb yopgan mavzu — yangi xabar kelsa qayta ochiladi
        try:
            telegram.api('reopenForumTopic', _token=ega_token, chat_id=ega_chat, message_thread_id=kw['message_thread_id'])
        except telegram.TelegramXatosi:  # yopilmagan (TOPIC_NOT_MODIFIED) yoki o'chirilgan — yuborishda aniqlanadi
            pass
    try:
        try:
            ega_id, sarlavha_id = _uzat(chat_id, m, tur, sarlavha, tugma, kw)
        except telegram.TelegramXatosi as e:  # ega mavzuni o'chirib yuborgan — yangisi ochiladi (bir marta)
            if 'message_thread_id' not in kw or 'thread' not in str(e).lower():
                raise
            kw['message_thread_id'] = _mavzu(chat_id, ega_chat, kim.split('\n')[0], ega_token, yangi=True)
            ega_id, sarlavha_id = _uzat(chat_id, m, tur, sarlavha, tugma, kw)
    except (telegram.TelegramXatosi, KeyError, TypeError):
        return [("Xabar yetib bormadi — birozdan keyin qayta yuboring.", None)]
    q = Murojaat.objects.create(chat_id=chat_id, foydalanuvchi_xabar_id=m['message_id'], ega_chat_id=ega_chat,
                                ega_xabar_id=ega_id, ega_sarlavha_id=sarlavha_id, xodim=xodim, salon=salon)
    from . import agent  # yoqilgan bo'lsa bilim bazasidan javob — bot jarayonida, navbat bilan
    navbatda = agent.navbatga(q, m.get('text') or m.get('caption') or '', agent.xabar_fayli(m))
    YordamRejimi.objects.filter(chat_id=chat_id).update(tugaydi=hozir + REJIM_MUDDATI)  # jimlik muddati qaytadan
    # Har xabarga matnli tasdiq: foydalanuvchi qo'llab-quvvatlash rejimida ekanini doim ko'rib tursin
    # (aks holda zakaz qidiruvi uchun yozgani ham egaga ketayotganini sezmay qolardi)
    if navbatda and platforma_sozlama().agent_avto:  # bot o'zi javob beradi yoki «mutaxassisga yo'naltirdim» deydi
        try:  # ortiqcha xabar o'rniga chat tepasida «yozmoqda…» (javob bir necha soniyada keladi)
            telegram.api('sendChatAction', chat_id=chat_id, action='typing', **({'_token': token} if token else {}))
        except telegram.TelegramXatosi:
            pass
        return []
    if tur != 'matn':
        return [(f"✅ {TURLAR[tur].capitalize()} mutaxassisga yuborildi — javob shu chatga keladi. Tugatish: /bekor.", None)]
    return [("✅ Qo'llab-quvvatlashga yuborildi — javob shu chatga keladi. Tugatish: /bekor.", None)]


def _reaksiya(chat_id, xabar_id, token=None):
    """Xabar qabul qilinganini 👌 bilan belgilaydi; eski Telegramda ko'rinmasa ham ish to'xtamaydi."""
    try:
        telegram.api('setMessageReaction', chat_id=chat_id, message_id=xabar_id,
                     reaction=[{'type': 'emoji', 'emoji': '👌'}], **({'_token': token} if token else {}))
    except telegram.TelegramXatosi:
        pass


# ---------- ega → foydalanuvchi ----------

def ega_javobi(ega_chat_id, m, token=None):
    """Ega murojaat xabariga «reply» qildi → javob foydalanuvchiga. Murojaatga tegishli bo'lsa True: bu xabar
    boshqa ishlovga (zakaz qidiruvi, to'lov ma'lumoti) o'tmaydi."""
    asl = m.get('reply_to_message') or {}
    if not asl.get('message_id'):
        return False
    q = Murojaat.objects.filter(ega_chat_id=ega_chat_id).filter(
        Q(ega_xabar_id=asl['message_id']) | Q(ega_sarlavha_id=asl['message_id'])).order_by('-id').first()
    kw = {'_token': token} if token else {}
    if not q:
        if (asl.get('text') or asl.get('caption') or '').startswith(SARLAVHA):  # murojaat ko'rinishida, lekin qatori yo'q
            _egaga(ega_chat_id, "❌ Javob yetkazilmadi: bu murojaat topilmadi.", kw)
            return True
        return False
    tur = xabar_turi(m)
    if not tur:
        _egaga(ega_chat_id, "❌ Bu turdagi javobni yuborib bo'lmaydi: matn, rasm, fayl yoki ovozli xabar yozing.", kw)
        return True
    xato = _foydalanuvchiga(q.chat_id, q.foydalanuvchi_xabar_id, ega_chat_id, m, tur, kw)
    if xato:
        _egaga(ega_chat_id, xato, kw)
        return True
    Murojaat.objects.filter(chat_id=q.chat_id, id__lte=q.id, javob_berildi__isnull=True).update(javob_berildi=timezone.now())
    _reaksiya(ega_chat_id, m['message_id'], token)
    if tur == 'matn':
        from . import agent
        agent.ega_javobi(q.chat_id, ega_chat_id, m['text'], None, token)
    return True


def _foydalanuvchiga(chat_id, javob_id, manba_chat, m, tur, kw):
    """Eganing javobi foydalanuvchiga (uning xabariga javob bo'lib). Xato bo'lsa — egaga aytiladigan matn, aks holda None."""
    javob = {'chat_id': chat_id, **kw}
    if javob_id:
        javob['reply_parameters'] = {'message_id': javob_id, 'allow_sending_without_reply': True}
    try:
        if tur == 'matn':
            telegram.api('sendMessage', text=f"{JAVOB_SARLAVHASI}:\n\n{m['text']}"[:4096], **javob)
        elif tur in IZOHLI_TURLAR:
            izoh = (m.get('caption') or '').strip()
            telegram.api('copyMessage', from_chat_id=manba_chat, message_id=m['message_id'],
                         caption=(JAVOB_SARLAVHASI + (f"\n\n{izoh}" if izoh else ''))[:1024], **javob)
        else:
            telegram.api('copyMessage', from_chat_id=manba_chat, message_id=m['message_id'], **javob)
    except telegram.TelegramXatosi as e:
        sabab = "foydalanuvchi botni bloklagan" if '403' in str(e) else 'Telegram xatosi, qayta yuboring'
        return f"❌ Javob yetkazilmadi: {sabab}."
    return None


# ---------- qo'llab-quvvatlash guruhi (mavzuli) ----------

def guruh_ishla(m, token=None):
    """Guruhdagi xabar. Bot boshqa guruhlarda ishlamaydi (xabarlarda mijoz ma'lumoti bor).

    `/murojaat_guruhi` — faqat platforma egasi yozsa, mavzular yoqilgan guruhni ulaydi. Ulangan guruhda mavzu ichida
    yozilgan xabar — o'sha mavzu egasiga (murojaatchiga) javob. Ishlangan bo'lsa qisqa natija, aks holda None.
    """
    from apps.tenants.models import platforma_sozlama
    kw = {'_token': token} if token else {}
    chat = m['chat']
    kimdan = m.get('from') or {}
    matn = (m.get('text') or '').strip()
    buyruq = matn.split()[0].split('@')[0].lower() if matn.startswith('/') else ''
    ps = platforma_sozlama()
    if buyruq == '/murojaat_guruhi':
        if not ps.telegram_chat_id or kimdan.get('id') != ps.telegram_chat_id:
            return None  # faqat ega ulaydi; boshqalarga javob berilmaydi
        if not chat.get('is_forum'):
            javob = "Avval guruh sozlamalarida «Mavzular» (Topics) ni yoqing, keyin /murojaat_guruhi ni qayta yozing."
        else:
            ps.yordam_guruh_id = chat['id']
            ps.save(update_fields=['yordam_guruh_id'])
            javob = ("✅ Murojaatlar shu guruhga keladi: har bir odamga alohida mavzu. Javob — o'sha mavzu ichida oddiy "
                     "yozing. Botni admin qiling («Mavzularni boshqarish» ruxsati bilan).")
        _guruhga(chat['id'], m.get('message_thread_id'), javob, kw)
        return javob
    if chat['id'] != ps.yordam_guruh_id or kimdan.get('is_bot') or not m.get('message_thread_id'):
        return None
    if kimdan.get('id') != ps.telegram_chat_id:
        return None  # guruhga boshqa a'zo qo'shilgan bo'lsa — uning xabari hech kimga ketmaydi
    q = YordamMavzu.objects.filter(guruh_id=chat['id'], mavzu_id=m['message_thread_id']).first()
    tur = xabar_turi(m)
    if not q or not tur:  # «General» yoki xizmat xabari (mavzu ochildi/yopildi)
        return None
    oxirgi = Murojaat.objects.filter(chat_id=q.chat_id, ega_chat_id=chat['id']).order_by('-id').first()
    xato = _foydalanuvchiga(q.chat_id, oxirgi.foydalanuvchi_xabar_id if oxirgi else None, chat['id'], m, tur, kw)
    if xato:
        _guruhga(chat['id'], m['message_thread_id'], xato, kw)
        return xato
    Murojaat.objects.filter(chat_id=q.chat_id, javob_berildi__isnull=True).update(javob_berildi=timezone.now())
    _reaksiya(chat['id'], m['message_id'], token)
    if tur == 'matn':  # «📚 Bazaga qo'shish» taklifi (agent bu savolni ko'rgan bo'lsa)
        from . import agent
        agent.ega_javobi(q.chat_id, chat['id'], m['text'], m['message_thread_id'], token)
    return 'yordam:guruh_javob'


def _guruhga(guruh_id, mavzu, matn, kw):
    try:
        telegram.api('sendMessage', chat_id=guruh_id, text=matn, **({'message_thread_id': mavzu} if mavzu else {}), **kw)
    except telegram.TelegramXatosi:
        pass


def _egaga(ega_chat_id, matn, kw):
    try:
        telegram.api('sendMessage', chat_id=ega_chat_id, text=matn, **kw)
    except telegram.TelegramXatosi:
        pass


def javobsizlar(hozir=None):
    """Oxirgi 7 kunda javob berilmagan murojaat qilgan chatlar soni («🏢 Platforma» uchun)."""
    hozir = hozir or timezone.now()
    return (Murojaat.objects.filter(javob_berildi__isnull=True, yaratilgan__gt=hozir - timedelta(days=7))
            .values('chat_id').distinct().count())
