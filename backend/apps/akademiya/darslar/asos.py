"""Dars pasporti va darslar uchun umumiy narsalar.

Har dars — `darslar/` ichidagi bitta fayl va undagi `DARS = Dars(...)`. Shu yozuvning o'zi darsning pasporti:
kim uchun, qaysi sahifada, boshlang'ich holat (urug'), topshiriq, yordam matnlari, tekshiruv va qachon haqiqiy
interfeys bilan solishtirilgani. Ro'yxat — `python manage.py dars_pasportlari`.

Tekshiruv — oddiy kod: o'quv salonining bazadagi holatiga (yoki o'quvchi tanlagan javobga) qaraydi va mezonlar
ro'yxatini qaytaradi. Dars faqat barcha mezon o'tganda «bajarildi» bo'ladi. Sanalar nisbiy — urug' ishga tushgan
kundan hisoblanadi, shuning uchun dars eskirmaydi.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Optional

from django.utils import timezone

from apps.bookings.models import Bron
from apps.catalog.models import Kategoriya, Libos
from apps.orders.models import Zakaz
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import Xodim

OYLAR = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']
HAFTA = ['dushanba', 'seshanba', 'chorshanba', 'payshanba', 'juma', 'shanba', 'yakshanba']

# Yo'nalishlar (bosqichlar xaritasidagi guruhlar) — tartibi shu
YONALISHLAR = [('kirish', 'Tanishuv'), ('sotuvchi', 'Mijoz va zakaz'), ('pul', 'Pul va kassa'), ('rahbar', 'Salonni boshqarish')]
# Personajlar: sotuvchi yo'lini Madina, rahbar yo'lini Nodira olib boradi
PERSONAJLAR = {'madina': {'ism': 'Madina', 'lavozim': 'sotuvchi'}, 'nodira': {'ism': 'Nodira', 'lavozim': 'salon rahbari'}}

MIJOZ_FIO, MIJOZ_TELEFON = 'Nilufar Karimova', '+998 90 123 45 67'
BAND_FIO, BAND_TELEFON = 'Dilfuza Rahimova', '+998 90 111 22 33'
IJARA, GAROV, AVANS = 300_000, 100_000, 100_000


def sana_matni(d):
    return f'{d.day}-{OYLAR[d.month - 1]} ({HAFTA[d.weekday()]})'


def som(n):
    return f'{n:,}'.replace(',', ' ') + " so'm"


def toy_sanalari(bugun=None):
    """Kamida 3 kundan keyingi shanba va undan keyingi dushanba — mijoz to'y uchun shu kunlarga so'raydi."""
    bugun = bugun or timezone.localdate()
    shanba = bugun + timedelta(days=3)
    shanba += timedelta(days=(5 - shanba.weekday()) % 7)
    return shanba, shanba + timedelta(days=2)


def holat_sanalari(h):
    return date.fromisoformat(h['dan']), date.fromisoformat(h['gacha'])


@dataclass
class Muhit:
    """Urug' va tekshiruvga beriladigan narsalar: o'quv saloni, o'quvchining shu salondagi xodimi va dars holati."""
    salon: object
    xodim: Xodim
    holat: dict

    @property
    def hamkasb(self):
        """O'quv salonidagi ikkinchi xodim (personaj): urug'dagi «boshqa xodim qilgan» ishlar uning nomidan yoziladi."""
        return Xodim.objects.filter(salon=self.salon, faol=True).exclude(id=self.xodim.id).order_by('id').first() or self.xodim


def mezon(ok, togri, xato):
    return {'ok': bool(ok), 'matn': togri if ok else xato}


def _hamma(salon, xodim):
    return True


def _bosh(h):
    return []


@dataclass(frozen=True)
class Dars:
    # --- pasport ---
    kod: str
    nomi: str
    yonalish: str                  # YONALISHLAR kalitlaridan biri
    personaj: str                  # PERSONAJLAR kalitlaridan biri
    sahifa: str                    # mashq ilovaning qaysi joyida bajariladi (o'quvchiga ko'rsatiladi)
    vaziyat: str                   # personaj aytadigan qisqa voqea (1–2 jumla)
    natija: str                    # «Dars oxirida … qila olasiz»
    tekshirilgan: str              # matn va tugma nomlari haqiqiy interfeys bilan solishtirilgan sana va commit
    # --- ish qismi ---
    urug: Callable                 # (Muhit) -> dars holati (dict, JSON ga yoziladi)
    topshiriq: Callable            # (holat) -> matn
    tekshir: Callable              # (Muhit, javob) -> [mezon, ...]
    ishora: str = ''               # 1-daraja yordam: yo'nalish beradi, javobni aytmaydi
    qadamlar: Callable = _bosh     # 2-daraja yordam: (holat) -> aniq qadamlar ro'yxati
    savol: Optional[Callable] = None   # (holat) -> {'matn', 'variantlar': [{'id', 'matn'}]} — javob panelda tanlanadi
    savollar: Optional[Callable] = None  # (holat) -> [Savol, ...] — bir necha vaziyatli savol (pastdagi `savol_tuz`)
    bilim: Optional[Callable] = None   # (holat) -> [qoida, ...] — savollardan OLDIN o'qitiladi: har savolning javobi shu
                                       # qoidalardan yoki qadam matnlaridan kelib chiqsin (test o'rgatishdan keyin)
    sahna: Optional[Callable] = None   # (holat) -> ko'rgazma bloklari: bot xabari yoki ekran ko'rinishi (pastga qarang)
    mos: Callable = _hamma         # shu o'quvchiga beriladimi (rol, kassa rejimi)
    yol: Callable = _bosh          # (holat) -> yo'naltirilgan qadamlar: ekranda faqat kerakli joy yoritiladi (pastga qarang)
    xp: int = 50                   # dars bajarilganda beriladigan tajriba bali
    xulosa: str = ''               # yakunda ko'rsatiladi: hozir nima qilindi va haqiqiy ishda bundan keyin nima keladi.
                                   # Dars jarayonning bir qismini o'rgatsa, shu yerda aniq aytiladi — yolg'on ko'nikma qolmasin
    namoyish: str = ''             # ekran yozuvi fayli (4-bosqichda Playwright skripti bilan olinadi); bo'sh — hali yo'q
    eslatma: str = field(default='', compare=False)  # pasportdagi ichki izoh (o'quvchiga ko'rinmaydi)


# ---------- umumiy urug': katalog ----------

LIBOSLAR = {  # kalit: (artikul, nomi, toifa, o'lcham)
    'band': ('M-001', 'Atlas', 'Milliy', '44'),
    'boshqa_olcham': ('M-002', 'Adras', 'Milliy', '46'),
    'togri': ('M-003', 'Zarbof', 'Milliy', '44'),
    'boshqa_toifa': ('O-001', 'Klassik', "Oq ko'ylak", '44'),
}


def katalog(m):
    """To'rtta libos: mos o'lchamdagi band, bo'sh lekin boshqa o'lchamdagi, mos va bo'sh, boshqa toifadagi."""
    toifalar = {n: Kategoriya.objects.create(salon=m.salon, nomi=n, tartib=i) for i, n in enumerate(['Milliy', "Oq ko'ylak"])}
    return {k: Libos.objects.create(salon=m.salon, kategoriya=toifalar[toifa], artikul=artikul, nomi=nomi, olcham=olcham,
                                    ijara_narxi=IJARA, zalog=GAROV, tannarx=3_000_000, qoshgan=m.hamkasb)
            for k, (artikul, nomi, toifa, olcham) in LIBOSLAR.items()}


def band_qil(m, libos, dan, gacha):
    """Boshqa mijozning tasdiqlangan broni: libos shu kunlarga band. Bron mustahkam qilinadi (avans olingandagi kabi),
    aks holda 24 soatdan keyin o'zi bo'shab, dars holati buzilardi."""
    z = zakaz_yaratish(salon=m.salon, xodim=m.hamkasb, telefon=BAND_TELEFON, fio=BAND_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[libos.id])
    z.holat = Zakaz.Holat.BRON
    z.save(update_fields=['holat'])
    Bron.objects.filter(zakaz=z).update(turi=Bron.Turi.MUSTAHKAM, muddati=None)
    return z


def toy_katalogi(m):
    """Ko'p darslarning boshlanishi: katalog va shanba–dushanbaga band bitta libos. (liboslar, dan, gacha) qaytadi."""
    dan, gacha = toy_sanalari()
    l = katalog(m)
    band_qil(m, l['band'], dan, gacha)
    return l, dan, gacha


# ---------- yo'naltirilgan qadamlar ----------
# Mashq erkin emas: har qadamda ilova ekranida faqat bitta joy yoritiladi, qolgani bosilmaydi (frontend: Yoritgich).
# Qadam — lug'at: `matn` (o'quvchiga ko'rsatma), `nishon` (yoritiladigan element), ixtiyoriy `muqobil`
# (nishon ekranda yo'q bo'lsa yoritiladigan element, masalan «Keyingi oy»), va qadam qachon tugashi:
#   amal='bos'  — nishon bosilganda (`ichki` berilsa — nishon ichidagi shu tugma bosilganda: o'quvchi o'zi tanlaydi);
#   amal='yoz'  — nishondagi maydon qiymati `kutilgan` ga to'g'ri kelganda ('raqam:…' — raqamlar shu bilan tugaydi,
#                 'uzunlik:N' — kamida N belgi, 'matn:…' — kichik harfda shu bo'lak bor);
#   `tayyor`    — shu element ekranda paydo bo'lganda (amaldan qat'i nazar);
#   amal='kor'  — faqat ko'rish: nishon yoritiladi, lekin bosilmaydi. Oxirgi qadamda — savollar shu paytda chiqadi;
#                 dars o'rtasida — o'quvchi ko'rib, paneldagi «Ko'rdim — davom etamiz» bilan o'tadi.
# `muqobil_matn` — muqobil yoritilganda panelda chiqadigan izoh.
# Element ta'rifi: `css` (bo'lmasa tugma va maydonlar), `matn` (aniq matn), `boshi` (matn boshlanishi),
# `ichida` (matnda bor), `label` (aria-label boshlanishi), `placeholder`.

# Telefonda (≤767 px) chap menyu yo'q: pastki panelda «Bosh», «Zakazlar», «Kassa» (yoki «Mijozlar»), «Profil»; qolgan
# bo'limlar «Profil» sahifasida. Kassa ichida tablar o'rniga Kassa bosh ekranidagi ro'yxat va «Kirim» / «Chiqim» tugmalari.
# Shuning uchun nishon — ro'yxat: birinchi topilgani yoritiladi (yoritgich.js `top`).
TEL_PANEL = {'Dashboard': 'Bosh'}
TEL_KASSA = {'Inkassatsiya': 'Pul topshirish'}           # Kassa bosh ekranidagi qator nomi
TEL_KASSA_AMAL = {"To'lov qabul": 'Kirim', 'Xarajat': 'Chiqim'}  # Kassa bosh ekranidagi katta tugmalar


def nav(nom, matn=None):
    """Asosiy bo'lim. Keng ekranda Kassa, Liboslar, Hisobotlar va Sozlama ochiq turganda chap panelda ularning ichki ro'yxati
    turadi — unda avval «‹ Asosiy» yoritiladi; telefonda bo'lim pastki panelda yoki «Profil» sahifasida."""
    return {'matn': matn or f"Menyudan «{nom}» bo'limini oching.", 'amal': 'bos',
            'nishon': [{'css': 'nav.pastki button', 'matn': nom},
                       {'css': 'nav.tab-bar button', 'matn': TEL_PANEL.get(nom, nom)},
                       {'css': '.profil-sahifa button.tb-qator', 'matn': nom}],
            'muqobil': [{'css': 'button.nav-orqaga'}, {'css': 'nav.tab-bar button', 'matn': 'Profil'}],
            'muqobil_matn': f"Avval yoritilgan tugmani bosing — bo'limlar ro'yxati ochiladi, keyin «{nom}» ni tanlaysiz."}


def tab(nom):
    nishon = [{'css': '[role=tab]', 'matn': nom}]
    if nom in TEL_KASSA_AMAL:
        nishon.append({'css': '.kassa-uy button.ku-amal', 'matn': TEL_KASSA_AMAL[nom]})
    else:
        nishon.append({'css': '.kassa-uy button.tb-qator', 'matn': TEL_KASSA.get(nom, nom)})
    return {'matn': f"«{nom}» bo'limini tanlang.", 'amal': 'bos', 'nishon': nishon,
            # telefonda Kassaning ichki sahifasidan bosh ekraniga qaytiladi
            'muqobil': {'css': 'button.kassa-orqaga'},
            'muqobil_matn': "Avval yoritilgan «‹ Kassa» ni bosing — Kassa bosh ekrani ochiladi."}


def kun(d, nima):
    """Kalendardagi kun. Kun boshqa oyda bo'lsa, avval «Keyingi oy» yoritiladi."""
    return {'matn': f"Kalendarda {nima} kunini bosing: {sana_matni(d)}.", 'amal': 'bos',
            'nishon': {'css': 'button', 'label': f'{d.day}-{OYLAR[d.month - 1]},'},
            'muqobil': {'css': 'button', 'label': 'Keyingi oy'},
            'muqobil_matn': "Kerakli kun boshqa oyda — avval ekranda yoritilgan «Keyingi oy» tugmasini bosing."}


def tugma(nom, matn=None, boshi=False):
    return {'matn': matn or f"«{nom}» tugmasini bosing.", 'amal': 'bos',
            'nishon': {'css': 'button', ('boshi' if boshi else 'matn'): nom}}


LIBOSLAR_ROYXATI = {'css': 'ul:has(> li .libos-rasm)'}  # Yangi zakaz → liboslar kartalari


# ---------- tajriba va darajalar ----------
# Daraja — o'quvchiga ochiq darslar balining ulushi bo'yicha (foizda): rahbar, sotuvchi va kassirning darslari soni har xil,
# shuning uchun qat'iy ball emas. «Usta» — yo'lning deyarli hammasi o'tilganda.
DARAJALAR = [(0, 'Yangi xodim'), (20, 'Shogird'), (50, 'Mustaqil xodim'), (90, 'Usta')]


def daraja(xp, jami):
    """XP va o'quvchiga ochiq jami ball bo'yicha daraja: raqami, nomi, shu daraja boshlangan va keyingisi boshlanadigan
    ball (oxirgi darajada keyingisi None)."""
    chegara = [-(-jami * foiz // 100) for foiz, _ in DARAJALAR]  # yuqoriga yaxlitlangan ball
    i = max(n for n, c in enumerate(chegara) if xp >= c)
    return {'raqam': i + 1, 'nomi': DARAJALAR[i][1], 'boshi': chegara[i], 'keyingi': chegara[i + 1] if i + 1 < len(chegara) else None}


# ---------- vaziyatli savollar ----------
# Ilovada mashq qilib bo'lmaydigan narsalar (kirish, Telegram tasdig'i, begona qurilma) vaziyat orqali o'rgatiladi:
# o'quvchiga haqiqiy xabar yoki ekran ko'rsatiladi va «nima qilasiz?» deb so'raladi. Har variantning o'z izohi bor —
# noto'g'ri tanlansa, nega noto'g'riligi aytiladi.
# Savol: {'matn': ..., 'variantlar': [(id, matn, to'g'rimi, izoh), ...]}; javob — tanlangan id'lar «|» bilan.
# Ko'rgazma bloki (sahna): {'tur': 'bot' | 'ekran', 'sarlavha': ..., 'matn': ..., 'tugmalar': [...]}.

def savol_json(savollar):
    """O'quvchiga beriladigan ko'rinish: to'g'ri javob va izohlarsiz."""
    return [{'matn': s['matn'], 'variantlar': [{'id': v[0], 'matn': v[1]} for v in s['variantlar']]} for s in savollar]


def savollarni_tekshir(savollar, javob):
    tanlangan = (javob or '').split('|')
    natija = []
    for i, s in enumerate(savollar):
        t = tanlangan[i] if i < len(tanlangan) else ''
        v = next((x for x in s['variantlar'] if x[0] == t), None)
        if v is None:
            natija.append(mezon(False, '', f"{i + 1}-savolga javob tanlanmagan."))
        else:
            natija.append(mezon(v[2], v[3], v[3]))
    return natija


def faqat_rahbar(salon, xodim):
    return xodim.rol == Xodim.Rol.RAHBAR


def sozlama_qatori(nom):
    """Sozlama bosh sahifasidagi bo'lim qatori (nomi bilan boshlanadi)."""
    # keng ekranda Sozlama ro'yxati chap panelda (.nav-sozlama-joy), torroqda — sahifaning o'zida
    return {'matn': f"«{nom}» bo'limini oching.", 'amal': 'bos',
            'nishon': {'css': 'main button, .nav-sozlama-joy button', 'boshi': nom}}


# Sozlama sahifasi amalni serverga yozib bo'lgach chiqaradigan xabar: qadam shundan keyin tugaydi (tekshiruv shoshilmasin)
SAQLANDI = {'css': '.soz-xabar:not(.xato)'}
# «Saqlash» qadami aynan «… saqlandi» xabari bilan tugaydi: oldingi amalning xabari («Filial qo'shildi») ekranda qolgan
# bo'lsa ham qadam o'z-o'zidan o'tib ketmasin
SAQLASH = {'matn': "Pastda «Saqlanmagan o'zgarishlar bor» chiqdi. «Saqlash» ni bosing — shundan keyingina kuchga kiradi.",
           'amal': 'bos', 'nishon': {'css': '.sozlama-saqlash button', 'matn': 'Saqlash'}, 'tayyor': {**SAQLANDI, 'ichida': 'saqlandi'}}


# ---------- zakaz kartasi va tasdiq oynasi ----------

ZAKAZ_OCHILDI = {'css': '.karta-tolovlar'}  # zakaz kartasi yuklangani (har rolda va har holatda bor)


def zakaz_qatori(fio):
    """Zakazlar ro'yxatidagi qator (keng ekranda jadval, telefonda karta)."""
    return {'css': 'tbody tr, button.zt-karta', 'ichida': fio}


def zakazni_och(fio, matn=None):
    return {'matn': matn or f"Ro'yxatdan {fio}ning zakazini oching.", 'amal': 'bos', 'nishon': zakaz_qatori(fio),
            'tayyor': ZAKAZ_OCHILDI}


# Kartadagi kam ishlatiladigan amallar «Boshqa amallar» ichida yig'ilgan; ochiq bo'lsa qadam o'zi o'tadi
BOSHQA_AMALLAR = {'matn': "Kam ishlatiladigan amallar yig'ib qo'yilgan. «Boshqa amallar» ni oching.", 'amal': 'bos',
                  'nishon': {'css': 'details.boshqa-amallar > summary'}, 'tayyor': {'css': 'details.boshqa-amallar[open]'}}


def amal_bolimi(nom, matn=None):
    """«Boshqa amallar» ichidagi bo'lim (nomi shu so'z bilan boshlanadi)."""
    return {'matn': matn or f"«{nom}» bo'limini oching.", 'amal': 'bos',
            'nishon': {'css': 'details.boshqa-amallar details.amal > summary', 'boshi': nom},
            'tayyor': {'css': 'details.boshqa-amallar details.amal[open] > summary', 'boshi': nom}}


def tasdiq(nom, matn=None, tayyor=None):
    """Tasdiq oynasidagi tugma («Ha, …»)."""
    q = {'matn': matn or f"Tizim qayta so'rayapti. Tasdiqlang: «{nom}».", 'amal': 'bos',
         'nishon': {'css': '[role=alertdialog] button', 'matn': nom}}
    if tayyor:
        q['tayyor'] = tayyor
    return q


TASDIQ_OYNASI = {'css': '[role=alertdialog]'}


def otgan_sanaga(z, dan, gacha):
    """Zakaz sanalarini o'tmishga suradi (kechikkan yoki eski zakaz): xizmatlar o'tgan sanaga zakaz ochmaydi.
    Bron olib tashlanadi — muddati tugagan (testlardagi usul bilan bir xil)."""
    Zakaz.objects.filter(id=z.id).update(olib_ketish=dan, qaytarish=gacha)
    Bron.objects.filter(zakaz=z).delete()
    z.olib_ketish, z.qaytarish = dan, gacha
    return z


def pulchi(m):
    """Urug'da pul bilan ishlaydigan xodim: o'quvchi pul olmasa (alohida kassir rejimidagi sotuvchi) — hamkasbi."""
    from apps.cash.services import pul_oladimi
    return m.xodim if pul_oladimi(m.salon, m.xodim) else m.hamkasb


def faqat_xodim(salon, xodim):
    """Sotuvchi va kassirga (rahbar bu ishni o'z darslarida boshqa tomondan ko'radi)."""
    return xodim.rol != Xodim.Rol.RAHBAR
