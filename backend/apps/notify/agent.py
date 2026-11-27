"""Qo'llab-quvvatlash agenti: murojaatga **faqat bilim bazasi asosida** javob yozadi (DeepSeek yoki OpenAI).

Egasi: «aqlli javob bersin, lekin o'ylab topmasin». Shuning uchun:
- Modelga faqat faol maqolalar (raqam, savol, javob) beriladi; ko'rsatma — faqat shu ma'lumotdan, qisqa javob yozish,
  bazada yo'q bo'lsa `null`. Model qaysi maqolalardan foydalanganini (`manbalar`) qaytaradi.
- Kod tekshiradi: javob bo'sh emas, uzun emas, manbalar bo'sh emas va hammasi yuborilgan faol maqolalardan.
  Aks holda — «topilmadi» (savol egaga o'tadi).
- Kafolat — tasdiq: taklif javob matni va manba maqolalar bilan egaga chiqadi, foydalanuvchiga faqat ega
  «✅ Yuborish» ni bosganda ketadi. «✏️ Tahrirlash» — matn nusxalash uchun chiqadi; ega tuzatib yozgan javob
  foydalanuvchiga boradi va bazaga o'zi qo'shiladi. Noto'g'ri bo'lsa — «❌ Kerak emas».
- Kontekst: shu foydalanuvchining oxirgi soatlardagi savol-javoblari (yashirilgan matn), uning saloni
  sozlamalari hamda roli va salon bazasidagi jonli holat — savoldagi zakazlar va uning kassa holati
  (`agent_malumot.py`; mijoz ismi, telefoni, salon nomi yuborilmaydi). Faqat jonli ma'lumotga tayangan javob
  (`malumot: true`, maqolasiz) ham qabul qilinadi; egaga taklif ostida qaysi ma'lumot ko'rilgani chiqadi.

Tasdiq rejimi: taklif guruhdagi murojaatchi mavzusiga «✅ Yuborish / ❌ Kerak emas» tugmalari bilan chiqadi; javob
faqat ega bosgandan keyin ketadi. Modelga faqat savol matni boradi (telefon, karta, email yashirilgan) — kim yozgani,
salon nomi yuborilmaydi. Ismlarni ishonchli yashirib bo'lmaydi: matnda ism bo'lsa, u ham boradi.

AI so'rovi bot jarayonida navbat bilan bajariladi (`navbatni_ishla`), foydalanuvchi xabarini qabul qilish uni
kutmaydi; xato jim (savol egada baribir bor), jurnalga yoziladi. Kalit faqat `.env` da: `DEEPSEEK_API_KEY` bo'lsa
DeepSeek, aks holda `OPENAI_API_KEY` (OpenAI).
"""
import html
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
TIMEOUT = 30            # soniya: AI javobini kutish (bot jarayoni shu payt boshqa ishni kutadi — navbat kichik)
MAQOLA_MAKS = 150       # modelga yuboriladigan maqolalar
SAQLASH_KUN = 30        # taklif qatori (yashirilgan savol matni) shuncha kun saqlanadi
TAKLIF_SARLAVHASI = "🤖 Bilim bazasidan javob taklifi"
SUHBAT_SOAT = 3         # shu vaqt ichidagi oldingi savol-javoblar kontekst sifatida beriladi
SUHBAT_MAKS = 6         # ko'pi bilan shuncha oldingi savol

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
    «JSON» so'zi va namuna bor), fikrlash rejimi o'chiq. Natija baribir `tanla` da tekshiriladi."""
    nomi, manzil, kalit, model = xizmat()
    if not kalit:
        raise AgentXatosi("AI kaliti (.env dagi DEEPSEEK_API_KEY yoki OPENAI_API_KEY) kiritilmagan.")
    tana = {'model': model, 'messages': xabarlar}
    if nomi == 'DeepSeek':
        tana.update(response_format={'type': 'json_object'}, thinking={'type': 'disabled'}, max_tokens=800)
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
        return None  # tushunarsiz javob — «topilmadi»


SXEMA = {'type': 'object', 'additionalProperties': False, 'required': ['javob', 'manbalar', 'malumot'],
         'properties': {'javob': {'type': ['string', 'null']}, 'manbalar': {'type': 'array', 'items': {'type': 'integer'}},
                        'malumot': {'type': 'boolean'}}}
KORSATMA = ("Siz Libosa (kelin liboslari salonlari uchun dastur) qo'llab-quvvatlash xodimisiz. Sizga bilim bazasi "
            "maqolalari (raqam, savol, javob) va foydalanuvchi savoli beriladi. Savolga FAQAT maqolalardagi ma'lumot "
            "asosida, o'zbek tilida (lotin), xushmuomala va qisqa (1–4 gap) javob yozing; kerak bo'lsa qadamlarni "
            "ketma-ket ayting. Maqolalarda yo'q narsani — tugma, bo'lim nomi, muddat, narx, imkoniyatni — qo'shmang "
            "va taxmin qilmang. Maqolalar savolga javob bermasa, savol boshqa mavzuda bo'lsa, faqat salom-alik, "
            "shikoyat yoki shaxsiy masala bo'lsa — javob null. «manbalar» — javobda foydalangan maqolalar raqamlari. "
            "Salon ma'lumoti berilgan bo'lsa, maqoladagi standart qiymat o'rniga shu salonnikini ayting (masalan, bron "
            "muddati). Savol beruvchining roliga mos javob bering: sotuvchi yoki kassir salon sozlamasini o'zgartira "
            "olmaydi — bunday ishni rahbar qilishini ayting. «Salon bazasidagi jonli ma'lumot» berilgan bo'lsa — bu "
            "shu salonning hozirgi haqiqiy holati (zakaz holati, qoldiq, garov, kassa): savol shunga tegishli bo'lsa, "
            "aniq sababni shu faktlardan ayting va nima qilish kerakligini maqolalardan qo'shing; faktlarni o'zgartirmang "
            "va berilmagan faktni o'ylab topmang. Jonli ma'lumotdan foydalansangiz «malumot»: true. Oldingi suhbat — "
            "faqat savolni tushunish uchun. Javob faqat JSON: {\"javob\": \"...\", \"manbalar\": [3], \"malumot\": false} "
            "yoki {\"javob\": null, \"manbalar\": [], \"malumot\": false}.")
JAVOB_MAKS = 1500       # model javobi bundan uzun bo'lsa — rad (tushunarsiz yoki keraksiz uzun)
BAZA_MAKS = 60000       # modelga yuboriladigan maqolalar matni (belgi)


def _qoida_matni(qoida):
    """[[30, 100], [7, 50], [0, 0]] → «30 kun va undan ko'p — 100%; 7–29 kun — 50%; 7 kundan kam — 0%»."""
    qismlar, oldingi = [], None
    for kun, foiz in qoida or []:
        if oldingi is None:
            oraliq = f"{kun} kun va undan ko'p"
        elif kun == 0:
            oraliq = f'{oldingi} kundan kam'
        else:
            oraliq = f'{kun}–{oldingi - 1} kun'
        qismlar.append(f'{oraliq} — {foiz}%')
        oldingi = kun
    return '; '.join(qismlar)


def salon_konteksti(murojaat):
    """Savol beruvchining roli va saloni qoidalari (shaxsiy ma'lumotsiz). Salon noma'lum bo'lsa — bo'sh."""
    from apps.tenants.models import sozlama
    s = murojaat.salon
    if not s:
        return ''
    so = sozlama(s)
    garov = {'pul': 'pul', 'hujjat': 'hujjat', 'tillo': 'tillo buyum'}
    ha = lambda b: 'ha' if b else "yo'q"  # noqa: E731
    qatorlar = [
        "Salon ma'lumoti (savol beruvchining saloni):",
        f"- savol beruvchining roli: {murojaat.xodim.get_rol_display().lower() if murojaat.xodim else 'aniqlanmagan'}",
        f"- kassa tartibi: {so.get_kassa_rejimi_display()}",
        f"- avanssiz (vaqtinchalik) bron muddati: {so.vaqtinchalik_bron_soat} soat",
        f"- tozalash buferi: {so.bufer_kun} kun",
        f"- garov turlari: {', '.join(garov[t] for t in so.zalog_turlari()) or 'yoqilmagan'}",
        ('- kechikish jarimasi: kuniga ' + f'{so.kechikish_kunlik_summa:,}'.replace(',', ' ') + " so'm")
        if so.kechikish_jarimasi else "- kechikish jarimasi: o'chiq",
        f"- avans qaytarish qoidasi: {_qoida_matni(so.qaytarish_qoidasi)}",
        f"- sotuvchi libos qo'sha oladi: {ha(so.sotuvchi_libos_qoshadi)}",
        f"- promokod va chegirma birga: {ha(so.promokod_chegirma_birga)}",
        f"- mavsumiy narx: {ha(so.mavsumiy_narx)}; sotuvchi bonusi: {ha(so.sotuvchi_bonusi)}; SMS eslatma: {ha(so.sms_eslatma)}",
        f"- obuna holati: {s.get_holat_display()}",
    ]
    return '\n'.join(qatorlar) + '\n\n'


def suhbat_konteksti(t):
    """Shu foydalanuvchining oxirgi `SUHBAT_SOAT` soatdagi oldingi savollari va unga ketgan javoblar (yashirilgan)."""
    oldingi = list(AgentTaklif.objects.filter(
        murojaat__chat_id=t.murojaat.chat_id, id__lt=t.id,
        yaratilgan__gt=timezone.now() - timedelta(hours=SUHBAT_SOAT)).order_by('-id')[:SUHBAT_MAKS])
    qatorlar = []
    for o in reversed(oldingi):
        qatorlar.append(f'Foydalanuvchi: {o.savol[:500]}')
        if o.ega_javobi:
            qatorlar.append(f"Qo'llab-quvvatlash: {yashir(o.ega_javobi)[:500]}")
        elif o.holat == AgentTaklif.Holat.YUBORILDI and o.javob:
            qatorlar.append(f"Qo'llab-quvvatlash: {o.javob[:500]}")
    return ('Oldingi suhbat (eskidan yangiga):\n' + '\n'.join(qatorlar) + '\n\n') if qatorlar else ''


class Taklif:
    """Model javobi (tekshirilgan): `matn` — foydalanuvchiga boradigan matn, `manbalar` — foydalanilgan maqolalar,
    `malumot` — salonning jonli ma'lumoti ishlatilgani (egaga nima ko'rilgani yoziladi)."""
    def __init__(self, matn, manbalar, malumot=''):
        self.matn, self.manbalar, self.malumot = matn, manbalar, malumot


def tanla(savol, kontekst='', jonli='', jonli_izoh=''):
    """Savolga bilim bazasi (va berilgan bo'lsa salonning jonli ma'lumoti) asosidagi javob (`Taklif`) yoki None.
    `kontekst` — salon sozlamalari va oldingi suhbat, `jonli` — `agent_malumot.jonli_malumot` bloki. Xatoda AgentXatosi."""
    maqolalar, hajm = [], 0
    for m in BilimMaqola.objects.filter(faol=True).order_by('id')[:MAQOLA_MAKS]:
        hajm += len(m.savol) + len(m.javob)
        if hajm > BAZA_MAKS:
            break
        maqolalar.append(m)
    if not maqolalar and not jonli:
        return None
    baza = '\n\n'.join(f'#{m.id}. Savol: {m.savol}\nJavob: {m.javob}' for m in maqolalar)
    natija = _sorov([{'role': 'system', 'content': KORSATMA},
                     {'role': 'user', 'content': f'Maqolalar:\n{baza}\n\n{kontekst}{jonli}Foydalanuvchi savoli:\n{yashir(savol)[:2000]}'}],
                    SXEMA)
    if not isinstance(natija, dict):
        return None
    matn, raqamlar = natija.get('javob'), natija.get('manbalar')
    malumot = bool(jonli) and natija.get('malumot') is True
    if not isinstance(matn, str) or not matn.strip() or len(matn) > JAVOB_MAKS or not isinstance(raqamlar, list):
        return None
    if not raqamlar and not malumot:
        return None  # na maqolaga, na salon ma'lumotiga tayangan — o'ylab topilgan bo'lishi mumkin
    if any(not isinstance(r, int) or isinstance(r, bool) for r in raqamlar):
        return None
    yuborilgan = {m.id: m for m in maqolalar}
    if any(r not in yuborilgan for r in raqamlar):
        return None  # yuborilmagan (yoki o'chiq) maqolaga tayangan — ishonchsiz
    return Taklif(matn.strip(), [yuborilgan[r] for r in dict.fromkeys(raqamlar)], jonli_izoh if malumot else '')


# ---------- navbat (bot jarayoni) ----------

def navbatga(murojaat, savol):
    """`murojaat_qabul` dan: agent yoqilgan va savol matn bo'lsa — navbatga (AI keyin, bot aylanishida)."""
    from apps.tenants.models import platforma_sozlama
    if not (savol or '').strip() or not sozlangan() or not platforma_sozlama().agent_yoqilgan:
        return None
    return AgentTaklif.objects.create(murojaat=murojaat, savol=yashir(savol)[:4096])


def navbatni_ishla(soni=2):
    """Navbatdagi takliflar (bir aylanishda ko'pi bilan `soni` ta): bazadan javob chiqsa — mavzuga taklif."""
    ishlandi = 0
    for t in (AgentTaklif.objects.filter(holat=AgentTaklif.Holat.NAVBATDA)
              .select_related('murojaat__salon', 'murojaat__xodim').order_by('id')[:soni]):
        if AgentTaklif.objects.filter(id=t.id, holat=AgentTaklif.Holat.NAVBATDA).update(holat=AgentTaklif.Holat.XATO) == 0:
            continue  # boshqa jarayon oldi
        try:
            from .agent_malumot import jonli_malumot
            taklif = tanla(t.savol, salon_konteksti(t.murojaat) + suhbat_konteksti(t), *jonli_malumot(t.murojaat, t.savol))
        except AgentXatosi as e:
            log.warning('Agent: %s', e)
            AgentTaklif.objects.filter(id=t.id).update(xato=str(e)[:300])
            continue
        if not taklif:
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
            xabar = telegram.api('sendMessage', text=taklif_matni(taklif)[:4096], reply_markup={'inline_keyboard': [[
                {'text': '✅ Yuborish', 'callback_data': f'ag:y:{t.id}'},
                {'text': '✏️ Tahrirlash', 'callback_data': f'ag:t:{t.id}'},
                {'text': '❌ Kerak emas', 'callback_data': f'ag:n:{t.id}'}]]}, **kw)
        except telegram.TelegramXatosi as e:
            log.warning('Agent taklifi yuborilmadi: %s', e)
            AgentTaklif.objects.filter(id=t.id).update(xato=str(e)[:300])
            continue
        AgentTaklif.objects.filter(id=t.id).update(holat=AgentTaklif.Holat.TAKLIF,
                                                   maqola=taklif.manbalar[0] if taklif.manbalar else None,
                                                   javob=taklif.matn, taklif_xabar_id=xabar.get('message_id'))
        ishlandi += 1
    return ishlandi


def taklif_matni(taklif):
    manba = [f"#{m.id} «{m.savol}»" for m in taklif.manbalar]
    if taklif.malumot:
        manba.append(f"📊 Salon bazasi: {taklif.malumot} — yuborishdan oldin ilovada tekshiring")
    return f"{TAKLIF_SARLAVHASI}:\n\n{taklif.matn}\n\n📚 Manba:\n" + '\n'.join(manba)


def tugma(c, token=None):
    """`ag:y:<id>` — yuborish, `ag:t:<id>` — tahrirlash, `ag:n:<id>` — kerak emas, `ag:b:<id>` — bazaga qo'shish.
    Faqat platforma egasi.

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
            matn = t and (t.javob or (t.maqola.javob if t.maqola else ''))
            if not ozgardi or not matn:
                javob = "Bu taklif allaqachon ko'rib chiqilgan."
            else:
                try:
                    telegram.api('sendMessage', chat_id=t.murojaat.chat_id,
                                 text=f"{JAVOB_SARLAVHASI}:\n\n{matn}"[:4096],
                                 reply_parameters={'message_id': t.murojaat.foydalanuvchi_xabar_id,
                                                   'allow_sending_without_reply': True}, **kw)
                    Murojaat.objects.filter(chat_id=t.murojaat.chat_id, javob_berildi__isnull=True).update(javob_berildi=timezone.now())
                    javob = '✅ Yuborildi'
                except telegram.TelegramXatosi as e:
                    AgentTaklif.objects.filter(id=tid).update(holat=AgentTaklif.Holat.TAKLIF, xato=str(e)[:300])
                    javob = '❌ Yetkazilmadi: ' + ("foydalanuvchi botni bloklagan" if '403' in str(e) else 'qayta bosing')
                    return javob
        elif q[1] == 't':  # matn nusxalash uchun chiqadi; ega tuzatib yozgan javob bazaga o'zi qo'shiladi (ega_javobi)
            ozgardi = AgentTaklif.objects.filter(id=tid, holat=AgentTaklif.Holat.TAKLIF).update(holat=AgentTaklif.Holat.TAHRIR)
            t = AgentTaklif.objects.filter(id=tid).first()
            if not ozgardi or not t:
                javob = "Bu taklif allaqachon ko'rib chiqilgan."
            else:
                m = c.get('message') or {}
                mavzu = m.get('message_thread_id')
                qayerga = "shu mavzuga yozing" if mavzu else "murojaat xabariga «reply» qilib yozing"
                try:
                    telegram.api('sendMessage', chat_id=(m.get('chat') or {}).get('id', platforma_sozlama().telegram_chat_id),
                                 text=f"<pre>{html.escape(t.javob[:3500])}</pre>\nMatnni bosib nusxalang, tuzating va {qayerga} — "
                                      "foydalanuvchiga boradi va bilim bazasiga o'zi qo'shiladi.",
                                 parse_mode='HTML', **({'message_thread_id': mavzu} if mavzu else {}), **kw)
                except telegram.TelegramXatosi:
                    pass
                javob = "✏️ Tahrirlanmoqda"
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
    va «📚 Bazaga qo'shish» taklif qilinadi — keyingi shunday savolga agent o'zi javob topadi.
    Ega «✏️ Tahrirlash» ni bosgan bo'lsa — tuzatilgan javob bazaga so'ramasdan qo'shiladi."""
    if not (matn or '').strip():
        return None
    yaqin = AgentTaklif.objects.filter(murojaat__chat_id=chat_id, bazada=False,
                                       yaratilgan__gt=timezone.now() - timedelta(days=3))
    tahrir = yaqin.filter(holat=AgentTaklif.Holat.TAHRIR).order_by('-id').first()
    if tahrir and AgentTaklif.objects.filter(id=tahrir.id, holat=AgentTaklif.Holat.TAHRIR, bazada=False).update(
            holat=AgentTaklif.Holat.YUBORILDI, ega_javobi=matn[:2000], bazada=True):
        m = BilimMaqola.objects.create(savol=tahrir.savol[:300], javob=matn[:2000], faol=True, manba=BilimMaqola.Manba.EGA)
        try:
            telegram.api('sendMessage', chat_id=guruh_id,
                         text=f"📚 Tuzatilgan javob bilim bazasiga qo'shildi (#{m.id}). «Libosa» ilovasida (Platforma → Bilim) "
                              "tahrirlash yoki o'chirish mumkin.",
                         **({'message_thread_id': mavzu} if mavzu else {}), **({'_token': token} if token else {}))
        except telegram.TelegramXatosi:
            pass
        return tahrir
    t = yaqin.exclude(holat__in=[AgentTaklif.Holat.YUBORILDI]).order_by('-id').first()
    if not t:
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
    """`/agent_sinov <savol>` — AI ishlayaptimi va qanday javob yozadi: egaga ko'rinadigan matn (hech kimga yuborilmaydi)."""
    if not savol.strip():
        return "Foydalanish: /agent_sinov savol matni\nMasalan: /agent_sinov PIN kodim esimdan chiqdi"
    soni = BilimMaqola.objects.filter(faol=True).count()
    if not soni:
        return "Bilim bazasida faol maqola yo'q. «Libosa» ilovasi → Platforma → Bilim bo'limida maqolalarni tekshirib yoqing."
    try:
        t = tanla(savol)
    except AgentXatosi as e:
        return f"❌ {xizmat()[0]} xatosi: {e}"
    if not t:
        return f"🤷 Bilim bazasida javob yo'q ({soni} ta faol maqola ichida). Bunday savol sizga o'tadi."
    manba = '\n'.join(f"#{m.id} «{m.savol}»" for m in t.manbalar)
    return f"✅ Javob taklifi:\n\n{t.matn}\n\n📚 Manba:\n{manba}"


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
