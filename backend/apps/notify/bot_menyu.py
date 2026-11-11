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
    'qidir': ('🔍 Zakaz qidirish', (R, S, K)),
    'libos': ("👗 Libos bo'shmi?", (R, S, K)),
}
EGA_AMALLARI = {'salonlar': '🏢 Salonlar', 'holat': '🩺 Holat'}
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


def matn_ishla(chat_id, matn):
    """Oddiy xabar (menyu tugmasi yoki erkin matn) → javoblar ro'yxati."""
    matn = (matn or '').strip()
    xx = xodimlar(chat_id)
    ega = egami(chat_id)
    if not xx and not ega:
        return [("Libosa boti. Ulash uchun ilovada «Telegramni ulash» tugmasini bosing.", None)]
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
            'bonus': _bonus}[amal](x)


# ---------- zakaz matni va qidiruv ----------

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
    return [(kunlik_matn(x.salon, timezone.localdate()), None)]


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


def _royxat(qs, sarlavha):
    zz = list(qs.select_related('mijoz').order_by('raqam')[:ROYXAT_MAKS + 1])
    if not zz:
        return f"{sarlavha}: yo'q"
    qatorlar = [f"#{z.raqam} · {z.mijoz.fio or 'mijoz'} · {z.mijoz.telefon}" for z in zz[:ROYXAT_MAKS]]
    if len(zz) > ROYXAT_MAKS:
        qatorlar.append('… va yana (ilovada to\'liq)')
    return f"{sarlavha} ({len(zz) if len(zz) <= ROYXAT_MAKS else str(ROYXAT_MAKS) + '+'}):\n" + '\n'.join(qatorlar)


def _zakazlar(x):
    from apps.orders.models import Zakaz
    return Zakaz.objects.filter(salon=x.salon)


def _ertaga(x):
    from apps.orders.views_royxat import BUGUN_FILTRLARI as F
    ertaga = timezone.localdate() + timedelta(days=1)
    return [(f"📅 Ertaga · {ertaga:%d.%m.%Y}\n\n" + _royxat(F['ertaga_olib'](_zakazlar(x)), 'Olib ketiladi') + '\n\n'
             + _royxat(F['ertaga_qaytar'](_zakazlar(x)), 'Qaytariladi'), None)]


def _ishlar(x):
    from apps.orders.views_royxat import BUGUN_FILTRLARI as F
    qismlar = [_royxat(F['bugun_olib'](_zakazlar(x)), 'Bugun olib ketiladi'),
               _royxat(F['bugun_qaytar'](_zakazlar(x)), 'Bugun qaytariladi')]
    if F['kechikkan'](_zakazlar(x)).exists():
        qismlar.append(_royxat(F['kechikkan'](_zakazlar(x)), '⚠️ Kechikkan'))
    return [(f"🗂 Bugungi ishlar · {timezone.localdate():%d.%m.%Y}\n\n" + '\n\n'.join(qismlar), None)]


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


# ---------- platforma egasi ----------

def _ega_amali(amal):
    bugun = timezone.localdate()
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
    from .models import Xabar
    s = platforma_sozlama()
    zaxira = (f'{timezone.localtime(s.oxirgi_zaxira):%d.%m.%Y %H:%M}' if s.oxirgi_zaxira else "hali yuborilmagan")
    eskirgan = bool(s.oxirgi_zaxira and s.oxirgi_zaxira < timezone.now() - timedelta(hours=36))
    navbat = Xabar.objects.filter(holat=Xabar.Holat.KUTILMOQDA, yaratilgan__gt=timezone.now() - timedelta(days=1)).count()
    return [('\n'.join([
        '🩺 Holat', "Baza: ishlayapti",
        f"Oxirgi zaxira nusxa: {zaxira}" + (' ⚠️ 36 soatdan eski' if eskirgan else ''),
        f"Yuborilishini kutayotgan xabarlar: {navbat}",
    ]), None)]


def obunasi_tugayotganlar(bugun, kun):
    """Sinov yoki obuna muddati `kun` kun ichida tugaydigan (yoki o'tib, ogohlantirish davrida turgan) salonlar."""
    qatorlar = []
    for s in Salon.objects.filter(chiqish_sanasi__isnull=True).exclude(holat=Salon.Holat.BLOKLANGAN).order_by('nomi'):
        muddat = s.obuna_muddati()
        if muddat is None or muddat > bugun + timedelta(days=kun) or muddat < bugun - timedelta(days=Salon.OGOHLANTIRISH_KUN):
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
    if qolgan > 0:
        return (f"⏳ {salon.nomi}: {tur.lower()} muddati {muddat:%d.%m.%Y} da tugaydi — {qolgan} kun qoldi.\n"
                "Salon uzilishsiz ishlashi uchun obunani uzaytiring.")
    if qolgan == 0:
        return f"⏳ {salon.nomi}: {tur.lower()} muddati bugun tugaydi.\nSalon uzilishsiz ishlashi uchun obunani uzaytiring."
    kun = Salon.OGOHLANTIRISH_KUN + qolgan  # «faqat ko'rish»gacha qolgan to'liq ish kunlari (bugundan tashqari)
    if kun <= 0:
        return (f"⚠️ {salon.nomi}: {tur.lower()} muddati {muddat:%d.%m.%Y} da tugagan. Ertadan salon «faqat ko'rish» rejimiga "
                "o'tadi: yangi zakaz ochilmaydi, boshlangan zakazlarni yakunlash mumkin. Obunani bugun uzaytiring.")
    return (f"⚠️ {salon.nomi}: {tur.lower()} muddati {muddat:%d.%m.%Y} da tugadi. Salon yana {kun} kun odatdagidek ishlaydi, "
            "keyin «faqat ko'rish» rejimiga o'tadi. Obunani uzaytiring.")


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
