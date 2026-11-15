"""K4 — Telegramni ulash. O'quv salonida Telegram ulanmaydi (tashqariga xabar chiqmasin — host.py), shuning uchun
vaziyatlar orqali. Matnlar kod bilan solishtirilgan: ulash — qo'ng'iroqcha menyusidagi blok (TelegramBlok.jsx: «/start <kod>»,
kod 15 daqiqa, «Telegramni uzish»); botdagi «⚙️ Sozlamalar» va «🌙 Tinch vaqt» — notify/bot_menyu.py (_sozlama_sahifasi)."""
from .asos import Dars, savollarni_tekshir

SAVOLLAR = [
    {'matn': "Qo'ng'iroqcha menyusida «Telegramni ulash» ni bosdingiz. Ekranda «/start …» ko'rinishidagi xabar chiqdi. "
             "Endi nima qilasiz?",
     'variantlar': [
         ('bot', "Telegramda Libosa botini ochib, shu xabarni yuboraman", True,
          "To'g'ri: «Botni ochish» ni bossangiz, xabar tayyor turadi — yuborasiz, xolos. Ulangach ilovadagi oyna o'zi yangilanadi."),
         ('rahbar', "Kodni rahbarga yuboraman — u ulab beradi", False,
          "Kod sizning Telegramingizni sizning hisobingizga bog'laydi. Uni boshqa odam yuborsa, sizning xabarlaringiz unga boradi."),
         ('kutaman', "Hech narsa — o'zi ulanadi", False,
          "O'zi ulanmaydi: kodni botga aynan siz yuborishingiz kerak. Kod 15 daqiqa amal qiladi."),
     ]},
    {'matn': "Telegramni ulamasangiz nima bo'ladi?",
     'variantlar': [
         ('ishlamaydi', "Ilovada ishlay olmayman", False,
          "Ilova ishlayveradi: eslatmalar bosh sahifada va qo'ng'iroqchada chiqadi. Telegram — qo'shimcha kanal."),
         ('otkazaman', "Eslatmalar faqat ilovada qoladi — ilova yopiq paytda ularni ko'rmayman", True,
          "To'g'ri: ertaga kim keladi, sizga pul topshirildi, chegirma tasdiqlandi — bularni ilovaga kirmaguncha bilmaysiz."),
         ('sms', "Xabarlar SMS bo'lib keladi", False, "Xodimga SMS yuborilmaydi — xabarlar faqat ilovada va Telegramda."),
     ]},
    {'matn': "Kechasi soat 23:00 da botdan xabar kelib uyg'otyapti. Nima qilasiz?",
     'variantlar': [
         ('uzaman', "Telegramni butunlay uzib qo'yaman", False,
          "Unda kunduzgi kerakli xabarlar ham kelmaydi. Buning uchun botda «🌙 Tinch vaqt» bor."),
         ('tinch', "Botda «⚙️ Sozlamalar» → «🌙 Tinch vaqt» ni yoqaman", True,
          "To'g'ri: masalan 22:00–08:00. Shu oraliqdagi odatiy xabarlar yig'ilib, ertalab bitta xabar bo'lib keladi. "
          "Xavfsizlik xabarlari (yangi qurilma, PIN bloklanishi) baribir darhol keladi."),
         ('chidayman', "Chidayman — boshqa yo'li yo'q", False, "Yo'li bor: botdagi «⚙️ Sozlamalar» → «🌙 Tinch vaqt»."),
     ]},
    {'matn': "Telefoningizni almashtirdingiz, Telegram akkauntingiz ham boshqa bo'ldi. Xabarlar hamon eski akkauntga boryapti. "
             "Nima qilasiz?",
     'variantlar': [
         ('qoldiraman', "Hech narsa — eskisi ham ishlayversin", False,
          "Eski akkaunt endi sizniki bo'lmasligi mumkin: mijoz ismi va summalar begona odamga boradi."),
         ('uzaman', "Ilovada qo'ng'iroqcha menyusidan «Telegramni uzish» ni bosib, yangisini qaytadan ulayman", True,
          "To'g'ri: uzish va boshqa Telegramga o'tkazish faqat ilovadan qilinadi — botning o'zidan emas."),
         ('botdan', "Botga «uz» deb yozaman", False,
          "Bot uzmaydi: uzish — ilovada, qo'ng'iroqcha menyusidagi «Telegramni uzish» tugmasi bilan."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return "Telegramni ulash haqida to'rtta vaziyat. Har birida o'zingiz nima qilishingizni tanlang."


def sahna(h):
    return [{'tur': 'ekran', 'sarlavha': "Ilova · qo'ng'iroqcha (🔔) menyusining pastki qismi",
             'matn': "Eslatmalarni Telegramda ham olish\nTelegramda botni oching va shu xabarni yuboring:\n/start 8f3k2a\n"
                     "Kod 15 daqiqa amal qiladi. Ulangach bu oyna o'zi yangilanadi.", 'tugmalar': ['Botni ochish']},
            {'tur': 'bot', 'sarlavha': 'Libosa bot · ⚙️ Sozlamalar',
             'matn': "🌙 Tinch vaqt\nShu oraliqda odatiy xabarlar yig'ilib turadi va tinch vaqt tugagach bitta xabar bo'lib keladi.",
             'tugmalar': ["O'chiq", '22:00–08:00', '21:00–09:00', '23:00–07:00']}]


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def bilim(h):
    return [
        "Ulash: ilovada qo'ng'iroqcha (🔔) menyusi → «Telegramni ulash». Ekranda «/start …» xabari chiqadi — «Botni ochish» ni bosib, "
        "uni Libosa botiga yuborasiz. Buni har kim o'z telefonida o'zi qiladi.",
        "Ulanmasa ham ilova ishlayveradi, lekin eslatmalar faqat ilovada qoladi: ilova yopiq paytda ularni ko'rmaysiz.",
        "Kechasi xabar bezovta qilmasligi uchun botda «⚙️ Sozlamalar» → «🌙 Tinch vaqt» bor: shu oraliqdagi xabarlar ertalab bitta "
        "bo'lib keladi.",
        "Telegram akkaunt almashsa: ilovada qo'ng'iroqcha menyusidan «Telegramni uzish», keyin yangisini qaytadan ulaysiz. "
        "Uzish faqat ilovadan qilinadi — botdan emas.",
    ]


DARS = Dars(
    kod='K4', nomi='Telegramni ulash', yonalish='kirish', personaj='madina',
    sahifa="Qo'ng'iroqcha menyusi · Telegram bot",
    vaziyat="Ilova doim ochiq turmaydi. Ertaga kim keladi, sizga pul topshirildi, rahbar chegirmani tasdiqladi — bu xabarlar "
            "Telegramga ham kelsa, hech narsa o'tib ketmaydi. Ulash bir daqiqalik ish.",
    natija="Telegramni o'z hisobingizga ulay olasiz, tungi xabarlarni to'xtatasiz va kerak bo'lsa uzasiz.",
    xulosa="Ulash: qo'ng'iroqcha (🔔) → «Eslatmalarni Telegramda ham olish» → «Telegramni ulash» → kodni botga yuborasiz. "
           "Botdagi «⚙️ Sozlamalar» da tinch vaqt, eslatma soati va qaysi xabarlar kelishini o'zingiz tanlaysiz. "
           "O'quv salonida Telegram ulanmaydi — buni haqiqiy ilovada bir marta qilib qo'ying.",
    tekshirilgan="2026-11-14 · kod bilan solishtirilgan (o'quv salonida Telegram ulanmaydi)",
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, sahna=sahna, savollar=lambda h: SAVOLLAR,
    ishora="Kod sizning Telegramingizni sizning hisobingizga bog'laydi. Uni kim yuborsa, xabarlar o'shanga boradi.",
    xp=40,
)
