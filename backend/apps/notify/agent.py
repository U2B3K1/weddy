"""Qo'llab-quvvatlash agenti: murojaatga bilim bazasidan mos javobni tanlaydi (DeepSeek yoki OpenAI) — **javobni o'zi yozmaydi**.

O'ylab topmaslik kodda kafolatlanadi, so'rov matniga ishonib emas:
- Modelga faqat faol maqolalarning raqami va savoli beriladi; u faqat bitta raqam yoki `null` qaytaradi (JSON sxema).
- Raqam yuborilganlar orasida bo'lmasa, javob tushunarsiz bo'lsa yoki xato bo'lsa — «topilmadi».
- Foydalanuvchiga borgan matn — bazadagi maqolaning o'zi (so'zma-so'z); modelning hech qanday matni ishlatilmaydi.

Tasdiq rejimi: taklif guruhdagi murojaatchi mavzusiga «✅ Yuborish / ❌ Kerak emas» tugmalari bilan chiqadi; javob
faqat ega bosgandan keyin ketadi. Modelga faqat savol matni boradi (telefon, karta, email yashirilgan) — kim yozgani,
salon nomi yuborilmaydi. Ismlarni ishonchli yashirib bo'lmaydi: matnda ism bo'lsa, u ham boradi.

AI so'rovi bot jarayonida navbat bilan bajariladi (`navbatni_ishla`), foydalanuvchi xabarini qabul qilish uni
kutmaydi; xato jim (savol egada baribir bor), jurnalga yoziladi. Kalit faqat `.env` da: `DEEPSEEK_API_KEY` bo'lsa
DeepSeek, aks holda `OPENAI_API_KEY` (OpenAI).
"""
import json
import logging
import re
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import telegram  # noqa: F401 — IPv4-birinchi ulanish (urllib ochuvchisi) shu modulda o'rnatiladi
from .models import AgentTaklif, BilimMaqola, Murojaat

log = logging.getLogger(__name__)
URL = 'https://api.openai.com/v1/chat/completions'
DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'
TIMEOUT = 15            # soniya: AI javobini kutish (bot jarayoni shu payt boshqa ishni kutadi — navbat kichik)
MAQOLA_MAKS = 150       # modelga yuboriladigan maqolalar
SAQLASH_KUN = 30        # taklif qatori (yashirilgan savol matni) shuncha kun saqlanadi
TAKLIF_SARLAVHASI = "🤖 Bilim bazasidan javob taklifi"

_TELEFON = re.compile(r'(?:\+?\d[\d\s\-()]{7,}\d)')
_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')
_KALIT = re.compile(r'sk-[\w*.-]+')  # xizmat xato matnida kalitning bir qismini qaytarishi mumkin — chatga chiqmaydi


class AgentXatosi(Exception):
    pass


def yashir(matn):
    """Modelga yuborishdan oldin: email, telefon va karta raqamlari (8+ raqamli ketma-ketlik) o'rniga belgi."""
    matn = _EMAIL.sub('[email]', matn or '')
    return _TELEFON.sub(lambda m: '[raqam]' if len(re.sub(r'\D', '', m.group())) >= 8 else m.group(), matn)


def xizmat():
    """(nomi, manzil, kalit, model): DeepSeek kaliti bo'lsa DeepSeek, aks holda OpenAI."""
    if settings.DEEPSEEK_API_KEY:
        return 'DeepSeek', DEEPSEEK_URL, settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_MODEL
    return 'OpenAI', URL, settings.OPENAI_API_KEY, settings.OPENAI_MODEL


def sozlangan():
    return bool(xizmat()[2])


def _sorov(xabarlar, sxema):
    """Chat Completions (OpenAI formati). Javob lug'ati, tushunarsiz bo'lsa None, xatoda AgentXatosi (kalit matnga chiqmaydi).

    OpenAI — Structured Outputs (qat'iy sxema). DeepSeek sxemani qo'llamaydi: JSON rejimi (`json_object`, ko'rsatmada
    «JSON» so'zi va namuna bor), fikrlash rejimi o'chiq. Qaytgan raqam baribir `tanla` da yuborilganlar bilan tekshiriladi."""
    nomi, manzil, kalit, model = xizmat()
    if not kalit:
        raise AgentXatosi("AI kaliti (.env dagi DEEPSEEK_API_KEY yoki OPENAI_API_KEY) kiritilmagan.")
    tana = {'model': model, 'messages': xabarlar}
    if nomi == 'DeepSeek':
        tana.update(response_format={'type': 'json_object'}, thinking={'type': 'disabled'}, max_tokens=50)
    else:
        tana['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'tanlov', 'strict': True, 'schema': sxema}}
    req = urllib.request.Request(manzil, data=json.dumps(tana).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {kalit}'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            javob = json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            tavsif = str((json.loads(e.read()).get('error') or {}).get('message', ''))[:200]
        except Exception:  # noqa: BLE001 — javob JSON bo'lmasligi mumkin
            tavsif = ''
        raise AgentXatosi(f'HTTP {e.code} {_KALIT.sub("[kalit]", tavsif)}'.strip())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise AgentXatosi(f'Ulanib bo\'lmadi: {type(e).__name__}')
    try:
        mazmun = javob['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise AgentXatosi(f'{nomi} javobi tushunarsiz')
    try:
        return json.loads(mazmun)
    except (TypeError, ValueError):
        return None  # tushunarsiz javob — «topilmadi» (modelning matni hech qachon ishlatilmaydi)


SXEMA = {'type': 'object', 'additionalProperties': False, 'required': ['id'],
         'properties': {'id': {'type': ['integer', 'null']}}}
KORSATMA = ("Siz Libosa (kelin liboslari saloni dasturi) qo'llab-quvvatlash xizmatidagi saralovchisiz. Foydalanuvchi "
            "savoli va tayyor maqolalar ro'yxati beriladi (raqam va savol). Savolga TO'LIQ javob beradigan bitta "
            "maqolaning raqamini qaytaring. Mos maqola bo'lmasa, savol boshqa narsa haqida bo'lsa, faqat salom-alik, "
            "shikoyat yoki shaxsiy masala bo'lsa, yoki ikkilansangiz — null qaytaring. Taxmin qilmang: noto'g'ri "
            "javobdan ko'ra null yaxshiroq. Javob faqat JSON: {\"id\": 12} yoki {\"id\": null}.")


def tanla(savol):
    """Savolga mos faol maqola yoki None. Xatoda AgentXatosi."""
    maqolalar = list(BilimMaqola.objects.filter(faol=True).order_by('id')[:MAQOLA_MAKS])
    if not maqolalar:
        return None
    royxat = '\n'.join(f'{m.id}. {m.savol}' for m in maqolalar)
    natija = _sorov([{'role': 'system', 'content': KORSATMA},
                     {'role': 'user', 'content': f'Maqolalar:\n{royxat}\n\nFoydalanuvchi savoli:\n{yashir(savol)[:2000]}'}],
                    SXEMA)
    raqam = natija.get('id') if isinstance(natija, dict) else None
    if not isinstance(raqam, int) or isinstance(raqam, bool):
        return None
    return next((m for m in maqolalar if m.id == raqam), None)  # faqat yuborilganlardan


# ---------- navbat (bot jarayoni) ----------

def navbatga(murojaat, savol):
    """`murojaat_qabul` dan: agent yoqilgan va savol matn bo'lsa — navbatga (AI keyin, bot aylanishida)."""
    from apps.tenants.models import platforma_sozlama
    if not (savol or '').strip() or not sozlangan() or not platforma_sozlama().agent_yoqilgan:
        return None
    return AgentTaklif.objects.create(murojaat=murojaat, savol=yashir(savol)[:4096])


def navbatni_ishla(soni=2):
    """Navbatdagi takliflar (bir aylanishda ko'pi bilan `soni` ta): mos maqola topilsa — mavzuga taklif."""
    ishlandi = 0
    for t in AgentTaklif.objects.filter(holat=AgentTaklif.Holat.NAVBATDA).select_related('murojaat').order_by('id')[:soni]:
        if AgentTaklif.objects.filter(id=t.id, holat=AgentTaklif.Holat.NAVBATDA).update(holat=AgentTaklif.Holat.XATO) == 0:
            continue  # boshqa jarayon oldi
        try:
            maqola = tanla(t.savol)
        except AgentXatosi as e:
            log.warning('Agent: %s', e)
            AgentTaklif.objects.filter(id=t.id).update(xato=str(e)[:300])
            continue
        if not maqola:
            AgentTaklif.objects.filter(id=t.id).update(holat=AgentTaklif.Holat.TOPILMADI)
            continue
        q = t.murojaat
        kw = {'chat_id': q.ega_chat_id}
        from .models import YordamMavzu
        mavzu = YordamMavzu.objects.filter(guruh_id=q.ega_chat_id, chat_id=q.chat_id).values_list('mavzu_id', flat=True).first()
        if mavzu:
            kw['message_thread_id'] = mavzu
        else:  # shaxsiy chat — qaysi murojaatga ekani ko'rinsin
            kw['reply_parameters'] = {'message_id': q.ega_xabar_id, 'allow_sending_without_reply': True}
        try:
            xabar = telegram.api('sendMessage', text=taklif_matni(maqola)[:4096], reply_markup={'inline_keyboard': [[
                {'text': '✅ Yuborish', 'callback_data': f'ag:y:{t.id}'},
                {'text': '❌ Kerak emas', 'callback_data': f'ag:n:{t.id}'}]]}, **kw)
        except telegram.TelegramXatosi as e:
            log.warning('Agent taklifi yuborilmadi: %s', e)
            AgentTaklif.objects.filter(id=t.id).update(xato=str(e)[:300])
            continue
        AgentTaklif.objects.filter(id=t.id).update(holat=AgentTaklif.Holat.TAKLIF, maqola=maqola,
                                                   taklif_xabar_id=xabar.get('message_id'))
        ishlandi += 1
    return ishlandi


def taklif_matni(maqola):
    return f"{TAKLIF_SARLAVHASI} (#{maqola.id} «{maqola.savol}»):\n\n{maqola.javob}"


def tugma(c, token=None):
    """`ag:y:<id>` — yuborish, `ag:n:<id>` — kerak emas, `ag:b:<id>` — bazaga qo'shish. Faqat platforma egasi.

    Holat bir marta o'zgaradi (atomik): ikki marta bosilsa ikkinchisi hech narsa qilmaydi."""
    from apps.tenants.models import platforma_sozlama

    from .yordam import JAVOB_SARLAVHASI
    kw = {'_token': token} if token else {}
    q = (c.get('data') or '').split(':')
    javob = "Bu tugma faqat platforma egasi uchun."
    if len(q) == 3 and q[2].isdigit() and c['from']['id'] == platforma_sozlama().telegram_chat_id:
        tid = int(q[2])
        if q[1] == 'y':
            with transaction.atomic():
                ozgardi = AgentTaklif.objects.filter(id=tid, holat=AgentTaklif.Holat.TAKLIF).update(holat=AgentTaklif.Holat.YUBORILDI)
            t = AgentTaklif.objects.select_related('murojaat', 'maqola').filter(id=tid).first()
            if not ozgardi or not t or not t.maqola:
                javob = "Bu taklif allaqachon ko'rib chiqilgan."
            else:
                try:
                    telegram.api('sendMessage', chat_id=t.murojaat.chat_id,
                                 text=f"{JAVOB_SARLAVHASI}:\n\n{t.maqola.javob}"[:4096],
                                 reply_parameters={'message_id': t.murojaat.foydalanuvchi_xabar_id,
                                                   'allow_sending_without_reply': True}, **kw)
                    Murojaat.objects.filter(chat_id=t.murojaat.chat_id, javob_berildi__isnull=True).update(javob_berildi=timezone.now())
                    javob = '✅ Yuborildi'
                except telegram.TelegramXatosi as e:
                    AgentTaklif.objects.filter(id=tid).update(holat=AgentTaklif.Holat.TAKLIF, xato=str(e)[:300])
                    javob = '❌ Yetkazilmadi: ' + ("foydalanuvchi botni bloklagan" if '403' in str(e) else 'qayta bosing')
                    return javob
        elif q[1] == 'n':
            ozgardi = AgentTaklif.objects.filter(id=tid, holat=AgentTaklif.Holat.TAKLIF).update(holat=AgentTaklif.Holat.RAD)
            javob = '❌ Yuborilmadi' if ozgardi else "Bu taklif allaqachon ko'rib chiqilgan."
        elif q[1] == 'b':
            t = AgentTaklif.objects.filter(id=tid, bazada=False).exclude(ega_javobi='').first()
            if t and AgentTaklif.objects.filter(id=tid, bazada=False).update(bazada=True):
                m = BilimMaqola.objects.create(savol=t.savol[:300], javob=t.ega_javobi[:2000], faol=True,
                                               manba=BilimMaqola.Manba.EGA)
                javob = f"📚 Bazaga qo'shildi (#{m.id}). «Libosa» ilovasida (Platforma → Bilim) tahrirlash mumkin."
            else:
                javob = "Bu savol allaqachon bazaga qo'shilgan."
        if c.get('message'):  # tugmalar olib tashlanadi, natija xabar ostida yoziladi
            m = c['message']
            matn = (m.get('text') or '')[:3900]
            try:
                telegram.api('editMessageText', chat_id=m['chat']['id'], message_id=m['message_id'],
                             text=f"{matn}\n\n{javob}", **kw)
            except telegram.TelegramXatosi:
                pass
    return javob


def ega_javobi(chat_id, guruh_id, matn, mavzu, token=None):
    """Ega mavzuda matn bilan javob berdi: shu murojaatchining oxirgi (3 kun ichidagi) agent qatoriga javob yoziladi
    va «📚 Bazaga qo'shish» taklif qilinadi — keyingi shunday savolga agent o'zi javob topadi."""
    t = (AgentTaklif.objects.filter(murojaat__chat_id=chat_id, bazada=False, yaratilgan__gt=timezone.now() - timedelta(days=3))
         .exclude(holat__in=[AgentTaklif.Holat.YUBORILDI]).order_by('-id').first())
    if not t or not (matn or '').strip():
        return None
    AgentTaklif.objects.filter(id=t.id).update(ega_javobi=matn[:2000])
    try:
        telegram.api('sendMessage', chat_id=guruh_id, text="📚 Shu savol va javobingizni bilim bazasiga qo'shaymi?",
                     reply_markup={'inline_keyboard': [[{'text': "📚 Bazaga qo'shish", 'callback_data': f'ag:b:{t.id}'}]]},
                     **({'message_thread_id': mavzu} if mavzu else {}), **({'_token': token} if token else {}))
    except telegram.TelegramXatosi:
        pass
    return t


def tozala():
    """Eski taklif qatorlari (yashirilgan savol matni bilan) — `SAQLASH_KUN` dan keyin o'chiriladi."""
    return AgentTaklif.objects.filter(yaratilgan__lt=timezone.now() - timedelta(days=SAQLASH_KUN)).delete()[0]


# ---------- ega buyruqlari ----------

def sinov(savol):
    """`/agent_sinov <savol>` — AI ishlayaptimi va qaysi maqola tanlanadi: egaga ko'rinadigan matn."""
    if not savol.strip():
        return "Foydalanish: /agent_sinov savol matni\nMasalan: /agent_sinov PIN kodim esimdan chiqdi"
    soni = BilimMaqola.objects.filter(faol=True).count()
    if not soni:
        return "Bilim bazasida faol maqola yo'q. «Libosa» ilovasi → Platforma → Bilim bo'limida maqolalarni tekshirib yoqing."
    try:
        m = tanla(savol)
    except AgentXatosi as e:
        return f"❌ {xizmat()[0]} xatosi: {e}"
    if not m:
        return f"🤷 Mos maqola topilmadi ({soni} ta faol maqola ichida). Bunday savol sizga o'tadi."
    return f"✅ Tanlandi: #{m.id} «{m.savol}»\n\nYuboriladigan javob:\n{m.javob}"


def holat_matni():
    from apps.tenants.models import platforma_sozlama
    ps = platforma_sozlama()
    faol = BilimMaqola.objects.filter(faol=True).count()
    qoralama = BilimMaqola.objects.filter(faol=False).count()
    qatorlar = ["🤖 Qo'llab-quvvatlash agenti",
                "Holat: " + ('yoqilgan (tasdiq rejimi)' if ps.agent_yoqilgan else "o'chiq"),
                f"AI xizmati: {xizmat()[0]}",
                f"Kalit: {'kiritilgan' if sozlangan() else 'kiritilmagan (.env → DEEPSEEK_API_KEY yoki OPENAI_API_KEY)'}",
                f"Model: {xizmat()[3]}",
                f"Bilim bazasi: {faol} ta faol, {qoralama} ta tekshirilmagan qoralama",
                '', "Sinash: /agent_sinov savol matni"]
    return '\n'.join(qatorlar)
