"""R14 — Yordam va obuna (rahbar). Texnik yordam ruxsati: platforma egasi salon ma'lumotini faqat rahbar bergan muddatda
va faqat o'qish uchun ko'radi (Sozlamalar.jsx «Texnik yordam», tenants.views_admin YordamRuxsatiView: 2 yoki 24 soat, har
kirish jurnalda, istalgan payt bekor). O'quv salonida ruxsat berilmaydi (host.py — faqat o'qish), shuning uchun bo'lim
ko'rsatiladi va savol beriladi. Obuna: muddat — botdagi «⚙️ Sozlamalar» → «💳 To'lov» (bot_menyu._tolov), tugashiga yaqin — ilovada banner
(App.jsx), tugagach — 7 kun ogohlantirish, keyin «faqat ko'rish» (Salon.OGOHLANTIRISH_KUN, obuna_xabar_matni)."""
from .asos import Dars, faqat_rahbar, nav, savollarni_tekshir, sozlama_qatori

SAVOLLAR = [
    {'matn': "Hisobotda tushunarsiz raqam chiqdi. Libosa yordamchisi: «Saloningiz ma'lumotini ko'rishim kerak», dedi. Nima qilasiz?",
     'variantlar': [
         ('parol', "Salon paroli va PIN kodimni yuboraman", False,
          "Hech qachon: parol va PIN hech kimga berilmaydi — yordamchiga ham. Buning uchun «Texnik yordam» ruxsati bor."),
         ('ruxsat', "Shu bo'limda 2 yoki 24 soatga ruxsat beraman", True,
          "To'g'ri: ruxsat muddatli, faqat ko'rish uchun va har kirish jurnalga yoziladi. Muddat tugagach o'zi yopiladi."),
         ('ozi', "Hech narsa — u baribir hammasini ko'ra oladi", False,
          "Ko'ra olmaydi: siz ruxsat bermaguningizcha platforma egasi salon ma'lumotini ochmaydi."),
     ]},
    {'matn': "Ruxsat berdingiz, muammo 20 daqiqada hal bo'ldi. Ruxsat muddati esa hali tugamagan. Nima qilasiz?",
     'variantlar': [
         ('qoladi', "Hech narsa — baribir o'zi tugaydi", False,
          "O'zi ham tugaydi, lekin kutish shart emas: ish bitgach «Ruxsatni bekor qilish» ni bosish — to'g'ri odat."),
         ('bekor', "Shu bo'limdagi «Ruxsatni bekor qilish» ni bosaman", True,
          "To'g'ri: ruxsat shu zahoti yopiladi. Kim qachon kirgani esa Sozlama → «Jurnal» da qoladi."),
         ('parol', "Salon parolini almashtiraman", False,
          "Parolning bunga aloqasi yo'q — yordamchi parol bilan kirmagan. Ruxsatni shu bo'limdan bekor qilasiz."),
     ]},
    {'matn': "Obuna qachon tugashini qayerdan bilasiz?",
     'variantlar': [
         ('bilmayman', "Bilib bo'lmaydi — tugaganda ilova yopilib qoladi", False,
          "Kutilmaganda yopilmaydi: tugashiga yaqin ilovada ogohlantirish chiqadi va botga xabar keladi."),
         ('tolov', "Botdagi «⚙️ Sozlamalar» → «💳 To'lov» dan: muddat va necha kun qolgani; yaqinlashganda ilova va bot o'zi eslatadi", True,
          "To'g'ri: «💳 To'lov» da muddat, tarif va to'lov ma'lumoti bor; to'lagach chekni shu yerdan yuborasiz."),
         ('sozlama', "Sozlama → «Rekvizitlar» dan", False,
          "Rekvizitlar — salonning nomi va manzili. Obuna muddati — botdagi «⚙️ Sozlamalar» → «💳 To'lov» da."),
     ]},
    {'matn': "Obuna muddati o'tib ketdi va to'lov qilinmadi. Salon bilan nima bo'ladi?",
     'variantlar': [
         ('ochadi', "Hamma ma'lumot o'chib ketadi", False,
          "Hech narsa o'chmaydi: zakazlar, mijozlar, liboslar joyida turadi. To'lovdan keyin salon to'liq ochiladi."),
         ('korish', "Yana bir hafta odatdagidek ishlaydi, keyin «faqat ko'rish»: yangi zakaz ochilmaydi, boshlanganlarini yakunlash mumkin", True,
          "To'g'ri: «faqat ko'rish» da to'lov, berish, qaytarish va smena ishlaydi — mijozlar oldida noqulay ahvolga tushmaysiz. "
          "Yangi zakaz, katalog va sozlamalar esa to'lovgacha yopiq."),
         ('darhol', "O'sha kuniyoq ilova butunlay yopiladi", False,
          "Darhol yopilmaydi: avval bir hafta ogohlantirish bilan ishlaydi, keyin ham boshlangan zakazlarni yakunlash mumkin."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return ("Sozlamadagi «Texnik yordam» bo'limini oching va unga qarab, to'rtta savolga javob bering: ikkitasi yordam ruxsati, "
            "ikkitasi obuna haqida.")


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Texnik yordam» bo'limiga kiring («Xavfsizlik» guruhida).",
            "Bo'limda ikki tugma bor: «2 soat» va «24 soat» — ruxsat shu muddatga beriladi.",
            "Obuna muddati esa ilovada emas — Telegram botdagi «⚙️ Sozlamalar» → «💳 To'lov» da."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Texnik yordam'),
            {'matn': "Bu — yordam ruxsati: platforma egasi salon ma'lumotini faqat siz bergan muddatda va faqat o'qish uchun ko'radi. "
                     "O'quv salonida tugmalar ishlamaydi — qarab chiqing va savollarga javob bering.", 'amal': 'kor',
             'nishon': {'css': '#soz-yordam'}}]


def bilim(h):
    return [
        "Yordamchiga parol yoki PIN berilmaydi. Shu bo'limda muddatli ruxsat beriladi: 2 yoki 24 soat, faqat ko'rish uchun, "
        "har kirish jurnalga yoziladi.",
        "Ish ertaroq bitsa — «Ruxsatni bekor qilish»: ruxsat shu zahoti yopiladi.",
        "Obuna muddati va necha kun qolgani — botdagi «⚙️ Sozlamalar» → «💳 To'lov» da (eslatma xabarining o'zida ham tugma bor). Muddat yaqinlashganda ilova va bot o'zi eslatadi.",
        "Muddat o'tib, to'lov qilinmasa: salon yana bir hafta odatdagidek ishlaydi, keyin «faqat ko'rish» ga o'tadi — yangi zakaz "
        "ochilmaydi, boshlanganlarini yakunlash mumkin. Hech narsa o'chmaydi.",
    ]


DARS = Dars(
    kod='R14', nomi='Yordam va obuna', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Texnik yordam · Telegram bot',
    vaziyat="Ikki holat kam bo'ladi, lekin bo'lganda nima qilishni bilish kerak: tizimda tushunarsiz narsa chiqdi va yordam kerak; "
            "obuna muddati tugayapti. Ikkalasida ham salon ma'lumoti sizning nazoratingizda qoladi.",
    natija="Yordamchiga ma'lumotni xavfsiz ko'rsatasiz va obuna muddatini kuzatib, salonni uzilishsiz ishlatasiz.",
    xulosa="Yordam kerak bo'lsa — parol emas, muddatli ruxsat: 2 yoki 24 soat, faqat ko'rish, har kirish jurnalda, istalgan payt "
           "bekor qilasiz. Obuna — botdagi «⚙️ Sozlamalar» → «💳 To'lov» da: muddat, to'lov ma'lumoti va chek yuborish. Muddat o'tsa ham salon "
           "birdan to'xtamaydi va hech narsa o'chmaydi. Shu bilan rahbar yo'li tugadi: salonni sozlash, nazorat qilish va "
           "natijani o'qish — hammasi qo'lingizda.",
    tekshirilgan='2026-11-14 · ishchi nusxa; obuna va ruxsat qoidalari kod bilan solishtirilgan',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Yordamchiga parol berilmaydi — unga muddatli ruxsat beriladi.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
