"""Botning so'rovga javob beradigan qismi: rolga qarab pastki menyu, zakaz qidiruvi, libos bandligi.

Bot faqat **ko'rsatadi** va mavjud qarorlarni tugma bilan qabul qiladi; zakaz ochish yoki to'lov kiritish yo'q —
ular ilovada ishonchli qurilma va PIN bilan himoyalangan.

Holat saqlanmaydi: bitta Telegram akkaunti bir nechta salonga ulangan bo'lsa, bot salonni inline tugma bilan
so'raydi (`m:<xodim_id>:<amal>`), javob o'sha tugmaning o'zidan aniqlanadi.

Har bir funksiya javoblar ro'yxatini qaytaradi: `[(matn, inline_tugmalar yoki None), ...]`.
"""
import re
from datetime import date, timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.tenants.models import Ariza, Salon, Xodim, platforma_sozlama, sozlama

from .services import som

R, S, K = Xodim.Rol.RAHBAR, Xodim.Rol.SOTUVCHI, Xodim.Rol.KASSIR

# amal kodi → (tugma matni, shu amalni ko'radigan rollar)
AMALLAR = {
    'bugun': ('📊 Bugun', (R,)),
    'kassa': ('💰 Kassa', (R, K)),
    'qaror': ('✅ Qaror kutmoqda', (R,)),
    'ertaga': ('📅 Ertaga', (R, S)),
    'ishlar': ('🗂 Bugungi ishlar', (S, K)),
    'bonus': ('🎁 Bonusim', (S,)),
    'tolov': ("💳 To'lov", (R,)),
    'sozlama': ('⚙️ Sozlamalar', (R, S, K)),
    'qidir': ('🔍 Zakaz qidirish', (R, S, K)),
    'libos': ("👗 Libos bo'shmi?", (R, S, K)),
}
EGA_AMALLARI = {'salonlar': '🏢 Salonlar', 'holat': '🩺 Holat', 'tolov_ega': "💳 To'lov ma'lumoti",
                'tolovlar': '💼 Obunalar'}
_KARTA = re.compile(r'(?<!\d)(?:\d[ -]?){15}\d(?!\d)')  # 16 raqamli karta — «nusxa olish» tugmasi uchun
# Ega shu xabarga javob (reply) qilib yozgan matn to'lov ma'lumoti bo'lib saqlanadi — holat saqlash shart emas
TOLOV_SORAV = "✍️ Yangi to'lov ma'lumotini shu xabarga javob qilib yozing"
TOLOV_MAKS = 1000
# Rahbar shu xabarga javob qilib yuborgan rasm/PDF — to'lov cheki (platforma egasiga uzatiladi)
CHEK_SORAV = "🧾 To'lov chekini shu xabarga javob qilib yuboring"
CHEK_KUNLIK_MAKS = 5
QIDIRUV_MAKS = 5
ROYXAT_MAKS = 15

QIDIR_YORDAM = ("Zakaz raqamini, mijoz telefonini (kamida 4 raqam) yoki ismini yozing.\n"
                "Masalan: 125 yoki 901234567 yoki Madina")
LIBOS_YORDAM = ("Libos kodi (yoki nomi) va sanani yozing.\nMasalan: A12 25.11 yoki A12 25.11-27.11")
_SANA = re.compile(r'(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?')


def xodimlar(chat_id):
    """Shu Telegram akkauntiga ulangan faol xodimlar (bloklangan salonlar tashqarida)."""
    return list(Xodim.objects.filter(telegram_id=chat_id, faol=True).exclude(salon__holat=Salon.Holat.BLOKLANGAN)
                .select_related('salon').order_by('salon__nomi'))


def egami(chat_id):
    return platforma_sozlama().telegram_chat_id == chat_id


def klaviatura(chat_id):
    """Pastki menyu: akkauntning barcha rollariga tegishli tugmalar (ega bo'lsa — platforma tugmalari ham)."""
    rollar = {x.rol for x in xodimlar(chat_id)}
    nomlar = [nom for nom, kimga in AMALLAR.values() if rollar & set(kimga)]
    if egami(chat_id):
        nomlar += list(EGA_AMALLARI.values())
    if not nomlar:
        return None
    return {'keyboard': [[{'text': n} for n in nomlar[i:i + 2]] for i in range(0, len(nomlar), 2)],
            'resize_keyboard': True}


def matn_ishla(chat_id, matn, javobga=''):
    """Oddiy xabar (menyu tugmasi yoki erkin matn) → javoblar ro'yxati.

    `javobga` — foydalanuvchi javob (reply) qilgan xabar matni: ega to'lov ma'lumotini shu yo'l bilan kiritadi.
    """
    matn = (matn or '').strip()
    xx = xodimlar(chat_id)
    ega = egami(chat_id)
    if not xx and not ega:
        return [("Libosa boti. Ulash uchun ilovada «Telegramni ulash» tugmasini bosing.", None)]
    # Javob rejimi ochiq turganda menyu tugmasi bosilsa, Telegram uni ham «javob» qilib yuboradi — u saqlanmaydi
    menyu_tugmasi = matn in EGA_AMALLARI.values() or matn in {nom for nom, _ in AMALLAR.values()}
    if ega and (javobga or '').startswith(TOLOV_SORAV) and not menyu_tugmasi and not matn.startswith('/'):
        return tolov_malumotini_saqla(matn)
    if ega and matn == '/vidjet':
        return _vidjet_sozlamasi()
    if ega and matn.startswith('/tolov'):  # zaxira yo'l: /tolov <matn>
        return tolov_malumotini_saqla(matn[6:].strip()) if matn[6:].strip() else _ega_amali('tolov_ega')
    for amal, nom in EGA_AMALLARI.items():
        if ega and matn == nom:
            return _ega_amali(amal)
    for amal, (nom, kimga) in AMALLAR.items():
        if matn == nom:
            mos = [x for x in xx if x.rol in kimga]
            if not mos:
                return [("Bu bo'lim sizning rolingiz uchun emas.", None)]
            if amal == 'qidir':
                return [(QIDIR_YORDAM, None)]
            if amal == 'libos':
                return [(LIBOS_YORDAM, None)]
            if len(mos) > 1:  # bir nechta salon — qaysi biri?
                return [("Qaysi salon?", [[{'text': x.salon.nomi[:40], 'callback_data': f'm:{x.id}:{amal}'}] for x in mos])]
            return amal_bajar(mos[0], amal)
    if not xx:
        return [("Pastdagi menyudan tanlang.", None)]
    if matn.startswith('/'):
        return [("Pastdagi menyudan tanlang yoki zakaz raqamini yozing.", None)]
    if _SANA.search(matn) and re.sub(_SANA, '', matn).strip(' -–—'):
        return [j for x in xx for j in libos_bandligi(x, matn, len(xx) > 1)]
    return zakaz_qidir(xx, matn)


def tugma_ishla(chat_id, data):
    """`m:<xodim_id>:<amal>` — salon tanlangan. Tugma bosgan akkaunt o'sha xodimning o'zi bo'lishi shart."""
    q = (data or '').split(':')
    if len(q) != 3 or not q[1].isdigit() or q[2] not in AMALLAR:
        return [("Noma'lum buyruq.", None)]
    x = next((x for x in xodimlar(chat_id) if x.id == int(q[1])), None)
    if not x or x.rol not in AMALLAR[q[2]][1]:
        return [("Bu amal sizga ruxsat etilmagan.", None)]
    return amal_bajar(x, q[2])


def amal_bajar(x, amal):
    return {'bugun': _bugun, 'kassa': _kassa, 'qaror': _qaror, 'ertaga': _ertaga, 'ishlar': _ishlar,
            'bonus': _bonus, 'tolov': _tolov, 'sozlama': _sozlamalar}[amal](x)


# ---------- zakaz matni va qidiruv ----------

def kop_filialli(salon):
    """Salonda ikki va undan ko'p faol filial bormi — bo'lsa bot xabarlarida filial nomi ham ko'rsatiladi."""
    from apps.tenants.models import Filial
    return Filial.objects.filter(salon=salon, faol=True).count() > 1


def zakaz_matni(z, sarlavha=''):
    """Zakazning to'liq qisqa ko'rinishi: yangi zakaz xabari va qidiruv natijasi uchun bir xil."""
    from apps.cash.services import tolangan_summa
    tolangan = tolangan_summa(z)
    liboslar = ', '.join(f'{p.libos.nomi} ({p.libos.artikul})' for p in z.pozitsiyalar.select_related('libos'))
    aks = ', '.join(f'{a.dona.aksessuar.nomi} ({a.dona.yorliq})' for a in z.aksessuarlar.select_related('dona__aksessuar'))
    qatorlar = [f'{sarlavha}🧾 Zakaz #{z.raqam} · {z.get_holat_display()}',
                f'👤 {z.mijoz.fio or "mijoz"} · {z.mijoz.telefon}',
                f'👗 {liboslar or "—"}']
    if aks:
        qatorlar.append(f'💍 {aks}')
    qatorlar.append(f'📅 {z.olib_ketish:%d.%m.%Y} → {z.qaytarish:%d.%m.%Y}')
    if z.filial_id and kop_filialli(z.salon):
        qatorlar.append(f'🏬 {z.filial.nomi}')
    pul = f'💵 Jami {som(z.jami)}'
    if z.holat != z.Holat.BEKOR:
        pul += f" · to'langan {som(tolangan)}" + (f' · qoldiq {som(z.jami - tolangan)}' if z.jami > tolangan else '')
    qatorlar.append(pul)
    if z.sotuvchi_id:
        qatorlar.append(f'Sotuvchi: {z.sotuvchi.ism}')
    return '\n'.join(qatorlar)


def zakaz_qidir(xx, matn):
    from apps.orders.models import Zakaz
    from apps.orders.views_royxat import q_filtri
    if len(matn) < 2 and not matn.isdigit():
        return [(QIDIR_YORDAM, None)]
    f, aniq = q_filtri(matn[:60])
    javoblar = []
    for x in xx:
        qs = Zakaz.objects.filter(f, salon=x.salon).select_related('mijoz', 'sotuvchi')
        topilgan = sorted(qs[:50], key=lambda z: (z.raqam != aniq, -z.raqam))
        bosh = f'{x.salon.nomi}\n' if len(xx) > 1 else ''
        javoblar += [(zakaz_matni(z, bosh), None) for z in topilgan[:QIDIRUV_MAKS]]
        if len(topilgan) > QIDIRUV_MAKS:
            javoblar.append((f"{bosh}Yana {len(topilgan) - QIDIRUV_MAKS}+ ta zakaz mos keldi — aniqroq yozing.", None))
    return javoblar or [("Zakaz topilmadi.\n" + QIDIR_YORDAM, None)]


def _sana(m, bugun):
    kun, oy, yil = int(m.group(1)), int(m.group(2)), m.group(3)
    try:
        if yil:
            return date(int(yil) + (2000 if len(yil) == 2 else 0), oy, kun)
        s = date(bugun.year, oy, kun)
        return s if s >= bugun else date(bugun.year + 1, oy, kun)  # yilsiz o'tgan sana — kelasi yil
    except ValueError:
        return None


def libos_bandligi(x, matn, salon_nomi=False):
    """«A12 25.11» yoki «A12 25.11-27.11» → libos shu kunlarda bo'shmi."""
    from apps.bookings.services import bosh_liboslar
    bugun = timezone.localdate()
    sanalar = [_sana(m, bugun) for m in _SANA.finditer(matn)][:2]
    q = re.sub(_SANA, '', matn).strip(' -–—')[:50]
    if not q or None in sanalar:
        return [(LIBOS_YORDAM, None)]
    dan, gacha = sanalar[0], sanalar[-1]
    if gacha < dan or dan < bugun:
        return [("Sana noto'g'ri: o'tgan kun yoki qaytarish olib ketishdan oldin.\n" + LIBOS_YORDAM, None)]
    natija = bosh_liboslar(x.salon, dan, gacha, q=q)
    bosh = f'{x.salon.nomi}\n' if salon_nomi else ''
    if not natija:
        return [(f"{bosh}«{q}» bo'yicha libos topilmadi.", None)]
    oraliq = f'{dan:%d.%m}' + (f'–{gacha:%d.%m}' if gacha != dan else '')
    qatorlar = [f'{bosh}{oraliq} uchun:']
    for libos, band in natija[:ROYXAT_MAKS]:
        if band:
            yaqin = getattr(libos, 'eng_yaqin_bosh', None)
            qatorlar.append(f"❌ {libos.artikul} · {libos.nomi} — band" + (f", {yaqin:%d.%m} dan bo'sh" if yaqin else ''))
        else:
            qatorlar.append(f"✅ {libos.artikul} · {libos.nomi} — bo'sh, {som(libos.ijara_narxi)}")
    return [('\n'.join(qatorlar), None)]


# ---------- menyu amallari ----------

def _bugun(x):
    from .management.commands.kunlik_hisobot import kunlik_matn
    matn = kunlik_matn(x.salon, timezone.localdate())
    if not platforma_sozlama().bot_vidjet:
        return [(matn, None)]
    from .vidjet import bugun_vidjeti
    return [(matn, bugun_vidjeti(x))]  # matn — vidjet izohi: vidjetni tanimaydigan Telegramda shu ko'rinadi


def _kassa(x):
    from apps.cash.models import Smena
    from apps.cash.services import kassa_hisobot, smena_usullari
    smenalar = list(Smena.objects.filter(salon=x.salon, yopilgan__isnull=True).select_related('ochgan', 'filial'))
    if not smenalar:
        return [("Kassa yopiq: ochiq smena yo'q.", None)]
    javob = []
    for s in smenalar:
        h = kassa_hisobot(s)
        naqdsiz = ' · '.join(f'{nom}: {som(summa)}' for nom, summa in _usullar(smena_usullari(s)))
        javob.append(('\n'.join(q for q in [
            f"💰 Kassa{' · ' + s.filial.nomi if s.filial_id else ''} — smena ochiq" + (f' ({s.ochgan.ism})' if s.ochgan_id else ''),
            f"Kassadagi naqd (hisob bo'yicha): {som(h['hisobdagi_qoldiq'])}",
            f"Bugungi naqd tushum: {som(h['tushum'])}",
            f"Naqdsiz — {naqdsiz}" if naqdsiz else '',
            f"Xarajat: {som(h['xarajatlar'])}" if h['xarajatlar'] else '',
        ] if q), None))
    return javob


def _usullar(usullar):
    """`smena_usullari` natijasidan naqd bo'lmagan (nom, summa) juftlari."""
    from apps.cash.models import Tolov
    nomlar = dict(Tolov.Usul.choices)
    return [(nomlar.get(u, u), s) for u, s in dict(usullar).items() if u != Tolov.Usul.NAQD and s]


def _qaror(x):
    """Rahbar qarorini kutayotgan hamma narsa — har biri o'z tugmasi bilan."""
    from apps.cash.models import Tolov
    from apps.cash.services import otkazma_tugmalari
    from apps.finance.models import Xarajat
    from apps.finance.services import xarajat_tugmalari, xarajat_xabar_matni
    from apps.orders.models import ChegirmaSorovi

    from .services import chegirma_matni_va_tugmalari
    javob = [chegirma_matni_va_tugmalari(s) for s in ChegirmaSorovi.objects.filter(
        salon=x.salon, holat=ChegirmaSorovi.Holat.KUTILMOQDA).select_related('zakaz', 'sotuvchi')[:10]]
    javob += [(xarajat_xabar_matni(xr), xarajat_tugmalari(xr)) for xr in Xarajat.objects.filter(
        salon=x.salon, holat=Xarajat.Holat.KUTILMOQDA).select_related('kiritgan')[:10]]
    for t in Tolov.objects.filter(salon=x.salon, tasdiq=Tolov.Tasdiq.KUTILMOQDA).select_related('zakaz', 'xodim')[:10]:
        z = f' · zakaz #{t.zakaz.raqam}' if t.zakaz_id else ''
        javob.append((f"💳 {t.get_usul_display()}: {som(t.summa)}{z}, qabul qildi: {t.xodim.ism}.\nHisobingizga tushdimi?",
                      otkazma_tugmalari(t)))
    return javob or [("Qaror kutayotgan narsa yo'q.", None)]


def _royxat(qs, sarlavha, filial=False):
    """`filial=True` — ko'p filialli salon: har qatorda zakaz qaysi filialda rasmiylashtirilgani ham."""
    zz = list(qs.select_related('mijoz', 'filial').order_by('raqam')[:ROYXAT_MAKS + 1])
    if not zz:
        return f"{sarlavha}: yo'q"
    qatorlar = [f"#{z.raqam} · {z.mijoz.fio or 'mijoz'} · {z.mijoz.telefon}"
                + (f' · {z.filial.nomi}' if filial and z.filial_id else '') for z in zz[:ROYXAT_MAKS]]
    if len(zz) > ROYXAT_MAKS:
        qatorlar.append('… va yana (ilovada to\'liq)')
    return f"{sarlavha} ({len(zz) if len(zz) <= ROYXAT_MAKS else str(ROYXAT_MAKS) + '+'}):\n" + '\n'.join(qatorlar)


def oz_filiali(x):
    """Filialga biriktirilgan sotuvchi/kassir — faqat o'z filiali ishlarini ko'radi; rahbar va biriktirilmaganlar — hammasini."""
    return x.filial_id if x.rol != R else None


def _zakazlar(x):
    from django.db.models import Q

    from apps.orders.models import Zakaz
    qs = Zakaz.objects.filter(salon=x.salon)
    if oz_filiali(x):  # filiali belgilanmagan (eski) zakazlar hammaga ko'rinadi
        qs = qs.filter(Q(filial_id=x.filial_id) | Q(filial__isnull=True))
    return qs


def _filial_yorligi(x):
    return f' · {x.filial.nomi}' if oz_filiali(x) else ''


def _ertaga(x):
    from apps.orders.views_royxat import BUGUN_FILTRLARI as F
    ertaga = timezone.localdate() + timedelta(days=1)
    kf = kop_filialli(x.salon) and not oz_filiali(x)
    return [(f"📅 Ertaga · {ertaga:%d.%m.%Y}{_filial_yorligi(x)}\n\n"
             + _royxat(F['ertaga_olib'](_zakazlar(x)), 'Olib ketiladi', kf) + '\n\n'
             + _royxat(F['ertaga_qaytar'](_zakazlar(x)), 'Qaytariladi', kf), None)]


def _ishlar(x):
    from apps.orders.views_royxat import BUGUN_FILTRLARI as F
    kf = kop_filialli(x.salon) and not oz_filiali(x)
    qismlar = [_royxat(F['bugun_olib'](_zakazlar(x)), 'Bugun olib ketiladi', kf),
               _royxat(F['bugun_qaytar'](_zakazlar(x)), 'Bugun qaytariladi', kf)]
    if F['kechikkan'](_zakazlar(x)).exists():
        qismlar.append(_royxat(F['kechikkan'](_zakazlar(x)), '⚠️ Kechikkan', kf))
    return [(f"🗂 Bugungi ishlar · {timezone.localdate():%d.%m.%Y}{_filial_yorligi(x)}\n\n" + '\n\n'.join(qismlar), None)]


def _bonus(x):
    from apps.finance.reports import sotuvchi_bonuslari
    bugun = timezone.localdate()
    r = sotuvchi_bonuslari(x.salon, bugun.year, bugun.month)
    if not r['yoqilgan']:
        return [("Bu salonda bonus hisoblanmaydi.", None)]
    men = next((q for q in r['sotuvchilar'] if q['id'] == x.id), None)
    if not men or not men['zakazlar']:
        return [(f"🎁 {bugun:%m.%Y}: hozircha bonus yo'q — bonus libos qaytarib olingandan keyin hisoblanadi.", None)]
    return [(f"🎁 Bonus · {bugun:%m.%Y}\nYopilgan zakazlar: {men['zakazlar']} ta, {som(men['tushum'])}\n"
             f"Bonus ({float(r['foiz']):g}%): {som(men['bonus'])}", None)]


# ---------- sozlamalar ----------
# Hammasi bitta xabar ichida: tugma bosilganda o'sha xabar yangilanadi (`s:<xodim_id>:<bo'lim>[:<qiymat>]`).

SOZLAMA_BOLIMLARI = {'tur': '🔔 Bildirishnoma turlari', 'yet': '📬 Yetkazish tartibi', 'esl': '⏰ Eslatma vaqti',
                     'tinch': '🌙 Tinch vaqt', 'muhim': '❗ Muhim xabarlar', 'maxfiy': '🙈 Maxfiylik',
                     'til': '🌐 Til va vaqt mintaqasi', 'hisob': '👤 Ulangan hisob'}


def _kabinet_manzili():
    from django.conf import settings
    return next((o for o in settings.CORS_ALLOWED_ORIGINS if o.startswith('https://')), '')


def _belgi(tanlangan):
    return '🔘 ' if tanlangan else '⚪ '


def _sozlama_sahifasi(x, bolim='bosh'):
    """Bitta sahifa: (matn, inline tugmalar)."""
    from .services import (ESLATMA_SOATLARI, JAMLANMA_SOATLARI, MUHIM_TOIFALAR, TINCH_VAQTLAR, XABAR_GURUHLARI, bot_soz)
    s = bot_soz(x)
    ochirilgan = set(x.bot_ochirilgan or [])
    guruhlar = {k: v for k, v in XABAR_GURUHLARI.items() if x.rol in v[2]}
    toifalar = {k: v for k, v in MUHIM_TOIFALAR.items() if x.rol in v[2]}
    tinch = f"{s['tinch'][0]}:00–{s['tinch'][1]:02d}:00" if s['tinch'] else "o'chiq"

    def t(matn, *qism):
        return {'text': matn, 'callback_data': ':'.join(['s', str(x.id), *map(str, qism)])}

    orqaga = [t('‹ Sozlamalar', 'bosh')]
    if bolim == 'tur':
        return (f"🔔 Bildirishnoma turlari · {x.salon.nomi}\nQaysi xabarlar kelib tursin? Bosib yoqing yoki o'chiring.\n"
                "✅ — keladi, 🔕 — kelmaydi.\n\nQaror va pul bilan bog'liq xabarlar (chegirma, xarajat, o'tkazma, "
                "yangi qurilma, qaytmagan libos, obuna) doim keladi.",
                [[t(('🔕 ' if k in ochirilgan else '✅ ') + nom, 'tur', k)] for k, (nom, _, _) in guruhlar.items()] + [orqaga])
    if bolim == 'yet':
        return ("📬 Yetkazish tartibi\nYangi zakaz, zakaz o'zgarishi, kassa farqi va yangi libos xabarlari qanday kelsin?\n\n"
                "Darhol — har biri yuz bergan paytda.\nJamlanma — kuniga bir marta, tanlangan soatda, bitta xabar bo'lib.\n\n"
                "Qaror so'rovlari, eslatmalar va hisobotlar jamlanmaga kirmaydi — ular o'z vaqtida keladi.",
                [[t(_belgi(s['jamlanma'] is None) + 'Darhol', 'yet', 'd')]]
                + [[t(_belgi(s['jamlanma'] == h) + f'Jamlanma — soat {h:02d}:00 da', 'yet', h)] for h in JAMLANMA_SOATLARI]
                + [orqaga])
    if bolim == 'esl':
        return ("⏰ Eslatma vaqti\nKunlik eslatmalar (ertaga olib ketadi, bugun qaytaradi, kechikdi, primerka) "
                "ertalab soat nechada kelsin?\n\nPrimerkaga bir soat qolganda yana bir marta eslatishni ham yoqish mumkin.",
                [[t(_belgi(s['eslatma'] == h) + f'{h:02d}:00', 'esl', h) for h in ESLATMA_SOATLARI],
                 [t(('✅ ' if s['primerka'] else '🔕 ') + 'Primerkadan 1 soat oldin', 'esl', 'p')], orqaga])
    if bolim == 'tinch':
        return ("🌙 Tinch vaqt\nShu oraliqda odatiy xabarlar yig'ilib turadi va tinch vaqt tugagach bitta xabar bo'lib keladi.\n\n"
                "Yangi qurilmadan kirish va PIN bloklanishi kabi xavfsizlik xabarlari tinch vaqtda ham darhol keladi. "
                "Qolgan muhim xabarlar — «Muhim xabarlar» bo'limida.",
                [[t(_belgi(not s['tinch']) + "O'chiq", 'tinch', 0)]]
                + [[t(_belgi(s['tinch'] == (b, o)) + f'{b}:00–{o:02d}:00', 'tinch', f'{b}-{o}')] for b, o in TINCH_VAQTLAR]
                + [orqaga])
    if bolim == 'muhim':
        return (f"❗ Muhim xabarlar\nTinch vaqtda{' (' + tinch + ')' if s['tinch'] else ''} qaysi muhim xabarlar baribir kelsin?\n"
                "✅ — tinch vaqtda ham darhol keladi, 🌙 — ertalabgacha kutadi.\n\n"
                "Xavfsizlik xabarlari (yangi qurilma, PIN bloklanishi) doim darhol keladi."
                + ('' if s['tinch'] else "\n\nHozir tinch vaqt o'chiq — bu tanlov u yoqilganda ishlaydi."),
                [[t(('🌙 ' if k in s['tinch_kutadi'] else '✅ ') + nom, 'muhim', k)] for k, (nom, _, _) in toifalar.items()]
                + [orqaga])
    if bolim == 'maxfiy':
        return ("🙈 Maxfiylik\nTo'liq matn — xabar chatda darhol o'qiladi.\n"
                "Yashirin — chatda faqat «yangi xabar» deb chiqadi; mazmuni «👁 Ko'rsatish» bosilganda ochiladi "
                "(telefon ekranida va chat ro'yxatida mijoz ismi, summa ko'rinmaydi).\n\n"
                "Kirish kodi va menyudan o'zingiz so'ragan ma'lumot har doim ochiq keladi.",
                [[t(_belgi(not s['maxfiy']) + "To'liq matn", 'maxfiy', 0)],
                 [t(_belgi(s['maxfiy']) + 'Yashirin', 'maxfiy', 1)], orqaga])
    if bolim == 'til':
        return ("🌐 Til va vaqt mintaqasi\nTil: o'zbekcha (lotin).\nVaqt: Toshkent vaqti (UTC+5), 24 soatlik ko'rinish.\n"
                "Sana: kun.oy.yil — masalan, 25.11.2026.\n\nHozircha boshqa til va vaqt mintaqasi yo'q.", [orqaga])
    if bolim == 'hisob':
        boshqalar = [b for b in xodimlar(x.telegram_id) if b.id != x.id] if x.telegram_id else []
        matn = (f"👤 Ulangan hisob\nSalon: {x.salon.nomi}\nXodim: {x.ism} · {x.get_rol_display()}\n"
                + (f"Filial: {x.filial.nomi}\n" if x.filial_id else '')
                + (''.join(f"\nShu Telegram yana ulangan: {b.salon.nomi} — {b.ism} ({b.get_rol_display()})" for b in boshqalar)
                   + '\n' if boshqalar else '')
                + "\nUlanishni uzish yoki boshqa Telegramga o'tkazish — ilovada: «Bildirishnomalar» oynasi → «Telegramni uzish».")
        manzil = _kabinet_manzili()
        return matn, ([[{'text': 'Ilovani ochish', 'url': manzil}]] if manzil else []) + [orqaga]
    yoqilgan = sum(1 for k in guruhlar if k not in ochirilgan)
    muhim = ('hammasi tinch vaqtda ham keladi' if not s['tinch_kutadi']
             else f"{len([k for k in toifalar if k in s['tinch_kutadi']])} tasi ertalabgacha kutadi")
    holat = {'tur': f'{yoqilgan}/{len(guruhlar)} yoqilgan',
             'yet': 'darhol' if s['jamlanma'] is None else f"jamlanma, soat {s['jamlanma']:02d}:00 da",
             'esl': f"{s['eslatma']:02d}:00" + (', primerkadan 1 soat oldin ham' if s['primerka'] else ''),
             'tinch': tinch, 'muhim': muhim, 'maxfiy': 'yashirin' if s['maxfiy'] else "to'liq matn",
             'til': "o'zbekcha, Toshkent vaqti", 'hisob': f'{x.ism} · {x.get_rol_display()}'}
    return (f"⚙️ Sozlamalar · {x.salon.nomi}\n\n" + '\n'.join(f'{nom}: {holat[k]}' for k, nom in SOZLAMA_BOLIMLARI.items()),
            [[t(nom, k)] for k, nom in SOZLAMA_BOLIMLARI.items()])


def _sozlamalar(x):
    return [_sozlama_sahifasi(x)]


def sozlama_tugma(chat_id, data):
    """`s:<xodim_id>:<bo'lim>[:<qiymat>]` — sahifani ochadi yoki qiymatni o'zgartiradi: (qisqa javob, matn, tugmalar).

    Har kim faqat o'z sozlamasini o'zgartiradi; rolga tegishli bo'lmagan guruh va ro'yxatda yo'q qiymat rad etiladi.
    """
    from .services import (ESLATMA_SOATLARI, JAMLANMA_SOATLARI, MUHIM_TOIFALAR, TINCH_VAQTLAR, XABAR_GURUHLARI)
    RAD = ("Bu amal sizga ruxsat etilmagan.", None, None)
    q = (data or '').split(':')
    if len(q) not in (3, 4) or not q[1].isdigit():
        return RAD
    x = next((x for x in xodimlar(chat_id) if x.id == int(q[1])), None)
    bolim, qiymat = q[2], (q[3] if len(q) == 4 else None)
    if not x or bolim not in ('bosh', *SOZLAMA_BOLIMLARI):
        return RAD
    if qiymat is None:
        return ('', *_sozlama_sahifasi(x, bolim))
    s = dict(x.bot_sozlama) if isinstance(x.bot_sozlama, dict) else {}
    son = int(qiymat) if qiymat.isdigit() else None
    javob = 'Saqlandi'
    if bolim == 'tur' and qiymat in XABAR_GURUHLARI and x.rol in XABAR_GURUHLARI[qiymat][2]:
        ochirilgan = set(x.bot_ochirilgan or []) ^ {qiymat}
        x.bot_ochirilgan = sorted(ochirilgan & set(XABAR_GURUHLARI))
        javob = XABAR_GURUHLARI[qiymat][0] + (": o'chirildi" if qiymat in ochirilgan else ': yoqildi')
    elif bolim == 'yet' and (qiymat == 'd' or son in JAMLANMA_SOATLARI):
        s['jamlanma'] = son
    elif bolim == 'esl' and son in ESLATMA_SOATLARI:
        s['eslatma'] = son
    elif bolim == 'esl' and qiymat == 'p':
        s['primerka'] = not s.get('primerka')
    elif bolim == 'tinch' and qiymat == '0':
        s['tinch'] = None
    elif bolim == 'tinch' and qiymat in {f'{b}-{o}' for b, o in TINCH_VAQTLAR}:
        s['tinch'] = [int(n) for n in qiymat.split('-')]
    elif bolim == 'muhim' and qiymat in MUHIM_TOIFALAR and x.rol in MUHIM_TOIFALAR[qiymat][2]:
        s['tinch_kutadi'] = sorted(set(s.get('tinch_kutadi') or []) ^ {qiymat})
    elif bolim == 'maxfiy' and qiymat in ('0', '1'):
        s['maxfiy'] = qiymat == '1'
    else:
        return RAD
    x.bot_sozlama = s
    x.save(update_fields=['bot_ochirilgan', 'bot_sozlama'])
    return (javob, *_sozlama_sahifasi(x, bolim))


# ---------- obuna to'lovi ----------

def obuna_holati_matni(salon, bugun=None):
    """Bir qator: sinov/obuna qachongacha va necha kun qoldi (rahbar va ega xabarlari uchun bir xil)."""
    bugun = bugun or timezone.localdate()
    muddat = salon.obuna_muddati()
    if muddat is None:
        return 'Muddat belgilanmagan'
    tur = 'Sinov' if salon.obuna_tugaydi is None else 'Obuna'
    qolgan = (muddat - bugun).days
    if qolgan > 0:
        return f'{tur} {muddat:%d.%m.%Y} gacha — {qolgan} kun qoldi'
    if qolgan == 0:
        return f'{tur} bugun tugaydi ({muddat:%d.%m.%Y})'
    return f'{tur} {muddat:%d.%m.%Y} da tugagan ({-qolgan} kun oldin)'


def _tolov(x):
    """Rahbar: obuna holati, tarif narxi va ega kiritgan to'lov ma'lumoti; «To'ladim» egaga xabar beradi."""
    s = x.salon
    qatorlar = [f"💳 To'lov · {s.nomi}", obuna_holati_matni(s)]
    if s.holat == Salon.Holat.FAQAT_KORISH:
        qatorlar.append("Salon hozir «faqat ko'rish» rejimida — to'lovdan keyin to'liq ochiladi.")
    if s.tarif_id:
        qatorlar.append(f'Tarif: {s.tarif.nomi}' + (f' — oyiga {som(s.tarif.oylik_narx)}' if s.tarif.oylik_narx else ''))
    from apps.tenants.models import ObunaTolovi
    if ObunaTolovi.objects.filter(salon=s, holat=ObunaTolovi.Holat.KUTILMOQDA).exists():
        qatorlar.append("⏳ To'lovingiz tekshirilmoqda — platforma egasi tasdiqlagach xabar keladi.")
    oxirgi = ObunaTolovi.objects.filter(salon=s, holat=ObunaTolovi.Holat.QABUL).order_by('-qaror_vaqt').first()
    if oxirgi:
        qatorlar.append(f"Oxirgi to'lov: {timezone.localtime(oxirgi.qaror_vaqt):%d.%m.%Y} — {oxirgi.oylar} oy"
                        + (f', {som(oxirgi.summa)}' if oxirgi.summa else ''))
    malumot = platforma_sozlama().tolov_malumoti.strip()
    if not malumot:
        qatorlar += ['', "To'lov ma'lumoti hali kiritilmagan. Platforma egasi bilan bog'laning."]
        return [('\n'.join(qatorlar), None)]
    karta = _KARTA.search(malumot)
    nusxa = ([[{'text': '📋 Karta raqamini nusxalash', 'copy_text': {'text': re.sub(r'\D', '', karta.group())}}]]
             if karta else [])
    qatorlar += ['', "To'lov qilish:", malumot, '', "To'lagach chekni yuboring — platforma egasiga boradi."]
    return [('\n'.join(qatorlar), nusxa + [[{'text': '🧾 Chek yuborish', 'callback_data': f'tc:{x.id}'}],
                                   [{'text': "✅ To'ladim (cheksiz)", 'callback_data': f'tl:{x.id}'}]])]


def chek_tugma(chat_id, data):
    """`tc:<xodim_id>` — rahbar chek yubormoqchi: javob (reply) so'raladi, salon nomi so'rovning o'zida."""
    q = (data or '').split(':')
    x = next((x for x in xodimlar(chat_id) if len(q) == 2 and q[1].isdigit() and x.id == int(q[1]) and x.rol == R), None)
    if not x:
        return [("Bu amal faqat salon rahbariga ruxsat etilgan.", None)]
    return [(f"{CHEK_SORAV}.\nSalon: {x.salon.nomi}\nRasm (skrinshot) yoki PDF fayl.",
             {'force_reply': True, 'input_field_placeholder': 'Chek rasmi'})]


def chek_ishla(chat_id, xabar, javobga=''):
    """Rasm yoki fayl keldi. Faqat rahbar va faqat chek so'roviga javob bo'lsa — egaga uzatiladi."""
    from django.core.cache import cache

    from .services import chek_egaga
    rahbarlar = [x for x in xodimlar(chat_id) if x.rol == R]
    if not rahbarlar:
        return [("Bot rasm va fayllarni qabul qilmaydi.", None)]
    if not (javobga or '').startswith(CHEK_SORAV):
        return [("To'lov chekini yuborish uchun: menyuda «💳 To'lov» → «🧾 Chek yuborish».", None)]
    nom = next((q[7:].strip() for q in javobga.split('\n') if q.startswith('Salon: ')), '')
    x = next((x for x in rahbarlar if x.salon.nomi == nom), None) or (rahbarlar[0] if len(rahbarlar) == 1 else None)
    if not x:
        return [("Salon aniqlanmadi. «💳 To'lov» → «🧾 Chek yuborish» ni qaytadan bosing.", None)]
    if xabar.get('photo'):
        tur, fayl = 'photo', xabar['photo'][-1]['file_id']  # oxirgisi — eng katta o'lcham
    else:
        hujjat = xabar.get('document') or {}
        mime = hujjat.get('mime_type') or ''
        if not (mime.startswith('image/') or mime == 'application/pdf'):
            return [("Faqat rasm yoki PDF fayl qabul qilinadi.", None)]
        tur, fayl = 'document', hujjat.get('file_id')
    kalit = f'chek:{x.salon_id}:{timezone.localdate()}'
    if (cache.get(kalit) or 0) >= CHEK_KUNLIK_MAKS:
        return [(f"Bugun {CHEK_KUNLIK_MAKS} ta chek yuborilgan. Platforma egasi ularni ko'rib chiqadi.", None)]
    if not chek_egaga(x, tur, fayl, (xabar.get('caption') or '').strip()):
        return [("Chek platforma egasiga yetmadi. Birozdan keyin qayta yuboring.", None)]
    cache.set(kalit, (cache.get(kalit) or 0) + 1, 24 * 3600)
    cache.set(f'toladim:{x.salon_id}:{timezone.localdate()}', 1, 24 * 3600)  # chek — «to'ladim» degani
    return [("✅ Chek platforma egasiga yuborildi. To'lov tekshirilgach obuna uzaytiriladi.", None)]


def tolov_malumotini_saqla(matn):
    matn = (matn or '').strip()
    if not matn:
        return [("Matn yuboring (rasm yoki fayl saqlanmaydi).", None)]
    if len(matn) > TOLOV_MAKS:
        return [(f"Matn juda uzun ({len(matn)} belgi). {TOLOV_MAKS} belgidan oshmasin.", None)]
    s = platforma_sozlama()
    s.tolov_malumoti = matn
    s.save(update_fields=['tolov_malumoti'])
    return [(f"✅ Saqlandi. Rahbarlar botdagi «💳 To'lov» bo'limida shuni ko'radi:\n\n{matn}", None)]


def ega_tugma(chat_id, data):
    """`e:<amal>` — platforma egasining inline tugmalari (faqat ega akkaunti)."""
    if not egami(chat_id):
        return [("Bu amal faqat platforma egasiga ruxsat etilgan.", None)]
    if data == 'e:tolov_yoz':
        return [(f"{TOLOV_SORAV}.\nMasalan: karta raqami, kimning nomida, aloqa telefoni. {TOLOV_MAKS} belgigacha.",
                 {'force_reply': True, 'input_field_placeholder': 'Karta, telefon, izoh'})]
    if data == 'e:holat':
        return [_holat_kartasi()]
    if data in ('e:ob_yaqin', 'e:ob_tugagan', 'e:ob_tekshir'):
        return _ega_obunalar(timezone.localdate(), data[5:])
    if data in ('e:vidjet_yoq', 'e:vidjet_och'):
        s = platforma_sozlama()
        s.bot_vidjet = data == 'e:vidjet_yoq'
        s.save(update_fields=['bot_vidjet'])
        return [("Vidjet yoqildi: rahbarlar «📊 Bugun» ni bosganda vidjet ko'radi." if s.bot_vidjet else
                 "Vidjet o'chirildi: «📊 Bugun» yana oddiy matn bo'lib keladi.", None)]
    if data == 'e:tolov_och':
        s = platforma_sozlama()
        s.tolov_malumoti = ''
        s.save(update_fields=['tolov_malumoti'])
        return [("To'lov ma'lumoti o'chirildi. Rahbarlar «hali kiritilmagan» degan yozuvni ko'radi.", None)]
    return [("Noma'lum buyruq.", None)]


# ---------- platforma egasi ----------

def _vidjet_sozlamasi():
    """`/vidjet` — ega namunani o'z telefonida ko'radi (o'ylab topilgan raqamlar), keyin rahbarlar uchun yoqadi."""
    from .vidjet import namuna_vidjeti
    yoqilgan = platforma_sozlama().bot_vidjet
    return [("Namuna: rahbarning «Bugun» vidjeti (raqamlar o'ylab topilgan). Vidjet ko'rinmasa — Telegram ilovangiz "
             "uni hali tanimaydi, rahbarlarda ham shunday bo'ladi.", namuna_vidjeti()),
            (f"Vidjet rahbarlar uchun hozir {'yoqilgan' if yoqilgan else 'o‘chiq'}.".replace('‘', "'"),
             [[{'text': "O'chirish", 'callback_data': 'e:vidjet_och'}] if yoqilgan else
              [{'text': 'Rahbarlar uchun yoqish', 'callback_data': 'e:vidjet_yoq'}]])]


def _kutayotgan_tolovlar(bugun):
    """To'lov tasdig'ini kutayotgan so'rovlar — har biri o'z qaror tugmalari bilan."""
    from apps.tenants.models import ObunaTolovi

    from .services import obuna_tugmalari
    return [(f"⏳ {t.salon.nomi} — {timezone.localtime(t.yaratilgan):%d.%m %H:%M}, "
             + ('chek yuborilgan' if t.chek_fayl else 'cheksiz')
             + (f' · {t.xodim.ism}' if t.xodim_id else '') + f'\n{obuna_holati_matni(t.salon, bugun)}', obuna_tugmalari(t))
            for t in ObunaTolovi.objects.filter(holat=ObunaTolovi.Holat.KUTILMOQDA)
            .select_related('salon__tarif', 'xodim').order_by('id')[:10]]


def _ega_obunalar(bugun, bolim=''):
    """«Obunalar»: jamlanma va uch ro'yxat — yaqin 7 kun, muddati tugagan, to'lovi tekshirilishi kerak."""
    from apps.tenants.models import ObunaTolovi
    yaqin = obuna_qatorlari(bugun, bugun, bugun + timedelta(days=7))
    tugagan = obuna_qatorlari(bugun, None, bugun - timedelta(days=1))
    if bolim == 'yaqin':
        return [("⏳ Yaqin 7 kunda tugaydi:\n" + '\n'.join(yaqin) if yaqin else "Yaqin 7 kunda muddati tugaydigan salon yo'q.", None)]
    if bolim == 'tugagan':
        return [("⚠️ Muddati tugagan:\n" + '\n'.join(tugagan) if tugagan else "Muddati tugagan salon yo'q.", None)]
    kutmoqda = _kutayotgan_tolovlar(bugun)
    if bolim == 'tekshir':
        return kutmoqda or [("Tekshirilishi kerak bo'lgan to'lov yo'q.", None)]
    qabul = ObunaTolovi.objects.filter(holat=ObunaTolovi.Holat.QABUL)
    oy = qabul.filter(qaror_vaqt__year=bugun.year, qaror_vaqt__month=bugun.month)
    qatorlar = ['💼 Obunalar', f"Yaqin 7 kunda tugaydi: {len(yaqin)}", f"Muddati tugagan: {len(tugagan)}",
                f"To'lovi tekshirilishi kerak: {len(kutmoqda)}", '',
                f"Shu oy: {oy.count()} ta to'lov, {som(oy.aggregate(s=Sum('summa'))['s'] or 0)}"]
    oxirgilar = list(qabul.select_related('salon').order_by('-qaror_vaqt')[:5])
    if oxirgilar:
        qatorlar += ['', 'Oxirgi to\'lovlar:'] + [
            f"• {timezone.localtime(t.qaror_vaqt):%d.%m} {t.salon.nomi} — {t.oylar} oy" + (f', {som(t.summa)}' if t.summa else ', summa kiritilmagan')
            for t in oxirgilar]
    return [('\n'.join(qatorlar), [
        [{'text': f'Yaqin 7 kun · {len(yaqin)}', 'callback_data': 'e:ob_yaqin'},
         {'text': f'Muddati tugagan · {len(tugagan)}', 'callback_data': 'e:ob_tugagan'}],
        [{'text': f'Tekshirish kerak · {len(kutmoqda)}', 'callback_data': 'e:ob_tekshir'}]])]


def _ega_amali(amal):
    bugun = timezone.localdate()
    if amal == 'tolovlar':
        return _ega_obunalar(bugun)
    if amal == 'tolov_ega':
        malumot = platforma_sozlama().tolov_malumoti.strip()
        tugmalar = [[{'text': "✍️ O'zgartirish" if malumot else '✍️ Kiritish', 'callback_data': 'e:tolov_yoz'}]]
        if malumot:
            tugmalar.append([{'text': "🗑 O'chirish", 'callback_data': 'e:tolov_och'}])
        return [("💳 To'lov ma'lumoti\nSalon rahbarlari botdagi «💳 To'lov» bo'limida shu matnni ko'radi.\n\n"
                 + (malumot or 'Hali kiritilmagan.'), tugmalar)]
    if amal == 'salonlar':
        salonlar = list(Salon.objects.filter(chiqish_sanasi__isnull=True).order_by('nomi'))
        sonlar = {}
        for s in salonlar:
            sonlar[s.get_holat_display()] = sonlar.get(s.get_holat_display(), 0) + 1
        qatorlar = [f'🏢 Salonlar: {len(salonlar)} ta'] + [f'{nom}: {n}' for nom, n in sonlar.items()]
        yaqin = obunasi_tugayotganlar(bugun, 7)
        if yaqin:
            qatorlar += ['', 'Muddati yaqin (7 kun):'] + yaqin
        yangi = Ariza.objects.filter(korilgan=False).count()
        if yangi:
            qatorlar += ['', f"Ko'rilmagan so'rovlar: {yangi}"]
        return [('\n'.join(qatorlar), None)]
    return [_holat_kartasi()]


def _holat_kartasi(hozir=None):
    """Platforma holati: fon vazifalari va bot oxirgi marta qachon ishlagani, zaxira nusxa, xabar navbati."""
    from . import yurak
    from .models import Xabar
    hozir = hozir or timezone.now()
    s = platforma_sozlama()
    kecha = hozir - timedelta(days=1)
    qatorlar = ['🩺 Platforma holati', f'Tekshirildi · {timezone.localtime(hozir):%H:%M}', '', 'Baza: ishlayapti']
    muammo = 0
    for _, sarlavha, vaqt, toxtagan in yurak.holatlar(hozir):
        if vaqt is None:
            qatorlar.append(f"{sarlavha}: hali ma'lumot yo'q")
        elif toxtagan:
            muammo += 1
            qatorlar.append(f"{sarlavha}: ⚠️ to'xtagan (oxirgi marta {timezone.localtime(vaqt):%d.%m %H:%M})")
        else:
            qatorlar.append(f"{sarlavha}: ishlayapti ({timezone.localtime(vaqt):%H:%M})")
    if not s.oxirgi_zaxira:
        qatorlar.append("Zaxira nusxa: hali yuborilmagan")
    else:
        eski = s.oxirgi_zaxira < hozir - timedelta(hours=36)
        muammo += eski
        qatorlar.append(f"Zaxira nusxa: {timezone.localtime(s.oxirgi_zaxira):%d.%m.%Y %H:%M}" + (' ⚠️ 36 soatdan eski' if eski else ''))
    navbat = Xabar.objects.filter(holat=Xabar.Holat.KUTILMOQDA, yaratilgan__gt=kecha).exclude(keyin__gt=hozir).count()
    xato = Xabar.objects.filter(holat=Xabar.Holat.XATO, yaratilgan__gt=kecha).count()
    qatorlar.append(f"Xabar navbati: {navbat} ta kutmoqda" + (f", 24 soatda {xato} tasi yetib bormadi" if xato else ''))
    qatorlar += ['', f"⚠️ E'tibor talab qiladi: {muammo}" if muammo else "Hammasi joyida."]
    tugmalar = [[{'text': '🔄 Yangilash', 'callback_data': 'e:holat'}]]
    if _kabinet_manzili():
        tugmalar.append([{'text': 'Panelni ochish', 'url': _kabinet_manzili() + '/#platforma'}])
    return '\n'.join(qatorlar), tugmalar


def obunasi_tugayotganlar(bugun, kun):
    """Sinov yoki obuna muddati `kun` kun ichida tugaydigan (yoki o'tib, ogohlantirish davrida turgan) salonlar."""
    return obuna_qatorlari(bugun, bugun - timedelta(days=Salon.OGOHLANTIRISH_KUN), bugun + timedelta(days=kun))


def obuna_qatorlari(bugun, dan, gacha):
    """Muddati [dan, gacha] oralig'iga tushgan salonlar, eng yaqini birinchi (`dan=None` — pastki chegara yo'q)."""
    qatorlar = []
    salonlar = [(s.obuna_muddati(), s) for s in
                Salon.objects.filter(chiqish_sanasi__isnull=True).exclude(holat=Salon.Holat.BLOKLANGAN).order_by('nomi')]
    for muddat, s in sorted(((m, s) for m, s in salonlar if m is not None), key=lambda q: q[0]):
        if muddat > gacha or (dan is not None and muddat < dan):
            continue
        tur = 'sinov' if s.obuna_tugaydi is None else 'obuna'
        qolgan = (muddat - bugun).days
        holat = 'bugun tugaydi' if qolgan == 0 else f'{qolgan} kun qoldi' if qolgan > 0 else f"{-qolgan} kun oldin tugagan"
        qatorlar.append(f'• {s.nomi} — {tur} {muddat:%d.%m}, {holat}' + (f' · {s.rahbar_telefon}' if s.rahbar_telefon else ''))
    return qatorlar


# Salon rahbarlariga eslatma kunlari: muddatgacha qolgan kun (manfiy — o'tganidan keyin).
# 3, 1, 0 — oldindan; -1 — tugadi; -OGOHLANTIRISH_KUN — «faqat ko'rish»dan oldingi oxirgi kun.
OBUNA_ESLATMA_KUNLARI = (3, 1, 0, -1, -Salon.OGOHLANTIRISH_KUN)


def obuna_xabar_matni(salon, muddat, qolgan):
    tur = 'Sinov' if salon.obuna_tugaydi is None else 'Obuna'
    qanday = "\nQanday to'lash — pastdagi menyuda «💳 To'lov»."
    if qolgan > 0:
        return (f"⏳ {salon.nomi}: {tur.lower()} muddati {muddat:%d.%m.%Y} da tugaydi — {qolgan} kun qoldi.\n"
                "Salon uzilishsiz ishlashi uchun obunani uzaytiring." + qanday)
    if qolgan == 0:
        return (f"⏳ {salon.nomi}: {tur.lower()} muddati bugun tugaydi.\n"
                "Salon uzilishsiz ishlashi uchun obunani uzaytiring." + qanday)
    kun = Salon.OGOHLANTIRISH_KUN + qolgan  # «faqat ko'rish»gacha qolgan to'liq ish kunlari (bugundan tashqari)
    if kun <= 0:
        return (f"⚠️ {salon.nomi}: {tur.lower()} muddati {muddat:%d.%m.%Y} da tugagan. Ertadan salon «faqat ko'rish» rejimiga "
                "o'tadi: yangi zakaz ochilmaydi, boshlangan zakazlarni yakunlash mumkin. Obunani bugun uzaytiring." + qanday)
    return (f"⚠️ {salon.nomi}: {tur.lower()} muddati {muddat:%d.%m.%Y} da tugadi. Salon yana {kun} kun odatdagidek ishlaydi, "
            "keyin «faqat ko'rish» rejimiga o'tadi. Obunani uzaytiring." + qanday)


def obuna_ogohlantirishi(bugun=None, hozir=None):
    """Obuna/sinov muddati haqida avtomatik eslatma (soatlik cron, soat 9 dan keyin; har eslatma bir marta).

    Asosiy xabar **salon rahbarlariga** boradi (muddatdan 3 va 1 kun oldin, tugash kuni, tugaganining ertasi va
    «faqat ko'rish»dan oldingi oxirgi kun) — platforma egasi hech kimga qo'lda yozmaydi. Egaga kuniga bitta xulosa:
    kimga eslatma ketdi va kimga yetib bormadi (rahbari Telegram ulamagan salon — faqat shular bilan o'zi bog'lanadi).
    Rahbarlarga yozilgan xabarlar sonini qaytaradi.
    """
    from .egaga import egaga_xabar
    from .services import rahbarlarga
    bugun = bugun or timezone.localdate()
    hozir = hozir or timezone.localtime().time()
    if hozir.hour < 9:
        return 0
    soni, xulosa = 0, []
    for s in Salon.objects.filter(chiqish_sanasi__isnull=True).exclude(holat=Salon.Holat.BLOKLANGAN).order_by('nomi'):
        muddat = s.obuna_muddati()
        if muddat is None or (muddat - bugun).days not in OBUNA_ESLATMA_KUNLARI:
            continue
        qolgan = (muddat - bugun).days
        yozilgan = [x for x in rahbarlarga(s, 'obuna_muddati', obuna_xabar_matni(s, muddat, qolgan),
                                           kalit=f'obuna:{muddat}:{qolgan}') if x]
        soni += len(yozilgan)
        yetdi = Xodim.objects.filter(salon=s, rol=R, faol=True, telegram_id__isnull=False).exists()
        holat = 'bugun tugaydi' if qolgan == 0 else f'{qolgan} kun qoldi' if qolgan > 0 else f'{-qolgan} kun oldin tugagan'
        xulosa.append(f'• {s.nomi} — {muddat:%d.%m}, {holat}: ' + ('rahbarga eslatma yuborildi' if yetdi else
                      "⚠️ rahbar Telegramga ulanmagan — o'zingiz bog'laning" + (f' ({s.rahbar_telefon})' if s.rahbar_telefon else '')))
    ps = platforma_sozlama()
    if xulosa and ps.obuna_xabar_sana != bugun and egaga_xabar('⏳ Obuna muddati:\n' + '\n'.join(xulosa)):
        ps.obuna_xabar_sana = bugun
        ps.save(update_fields=['obuna_xabar_sana'])
    return soni
