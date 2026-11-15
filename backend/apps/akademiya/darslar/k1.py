"""K1 — Kirish va PIN. Kirishni o'quv salonida mashq qilib bo'lmaydi (akademiyaga parolsiz kiriladi), shuning uchun
vaziyatlar orqali o'rgatiladi. Matnlar kod bilan solishtirilgan: PIN 5 marta xato — 15 daqiqa blok va rahbarga xabar
(tenants/views.py pin_tekshir), yangi qurilma rahbar ruxsatini kutadi (SalonLoginView), 10 daqiqa harakatsizlik (App.jsx)."""
from .asos import Dars, savollarni_tekshir

SAVOLLAR = [
    {'matn': "Hamkasbingiz PIN kodini unutdi: «Bir marta sizniki bilan kirib turay», deyapti. Nima qilasiz?",
     'variantlar': [
         ('beraman', "PIN kodimni aytaman — bir marta-ku", False,
          "PIN — sizning imzoingiz. U bilan qilingan har bir zakaz, to'lov va kassadagi farq sizning nomingizga yoziladi."),
         ('ozim', "O'zim kirib, planshetni unga beraman", False,
          "Bu ham xuddi PIN berishdek: hamkasbingiz qilgan hamma ish tizimda sizniki bo'lib ko'rinadi."),
         ('rahbar', "PIN bermayman — rahbar unga yangi PIN qo'yib beradi", True,
          "To'g'ri: PIN hech kimga berilmaydi. Unutilgan PIN'ni rahbar Sozlama → Xodimlar bo'limida almashtiradi."),
     ]},
    {'matn': "PIN kodni ketma-ket 5 marta xato terdingiz. Nima bo'ladi?",
     'variantlar': [
         ('hech', "Hech narsa — to'g'risini topguncha teraveraman", False,
          "Yo'q: 5 ta xatodan keyin kirish 15 daqiqaga to'xtaydi — begona odam PIN'ni taxmin qila olmasligi uchun."),
         ('blok', "Kirish 15 daqiqaga to'xtaydi va rahbarga xabar boradi", True,
          "To'g'ri: 15 daqiqa kutasiz yoki rahbar Telegramdagi «Blokdan chiqarish» tugmasi bilan darhol ochadi."),
         ('ochadi', "Hisobim butunlay o'chib ketadi", False,
          "Hisob o'chmaydi: kirish faqat 15 daqiqaga to'xtaydi va rahbarga xabar boradi."),
     ]},
    {'matn': "Salonga yangi planshet keldi. Salon logini kiritilgach ekranda «Qurilma rahbar ruxsatini kutmoqda» chiqdi. Nima qilasiz?",
     'variantlar': [
         ('buzuq', "Planshet buzilgan — eskisida ishlayveraman", False,
          "Planshet buzilmagan. Bu himoya: salon parolini bilgan begona odam o'z qurilmasidan kira olmasligi uchun."),
         ('kutaman', "Rahbarga aytaman: unga Telegramda «Ruxsat / Rad» so'rovi borgan", True,
          "To'g'ri: har yangi qurilmani rahbar tasdiqlaydi. Ruxsat berilishi bilan ekran o'zi ochiladi."),
         ('boshqa', "Parolni qayta-qayta kiritib ko'raman", False,
          "Foydasi yo'q: parol to'g'ri, qurilma esa rahbar ruxsatini kutyapti. Qayta kiritish rahbarga ortiqcha so'rov yuboradi."),
     ]},
    {'matn': "Mijoz bilan gaplashib, 10 daqiqa planshetga tegmadingiz. Ekran yana PIN so'rayapti. Bu nima?",
     'variantlar': [
         ('xato', "Tizim xatosi — rahbarga xabar beraman", False,
          "Bu xato emas: tizim 10 daqiqa harakatsizlikdan keyin o'zi chiqadi."),
         ('himoya', "Himoya: qarovsiz qolgan planshetda hech kim mening nomimdan ishlamasin", True,
          "To'g'ri: PIN'ni qayta terasiz va ishni davom ettirasiz. Planshetdan uzoqlashsangiz, o'zingiz ham «Ilovadan chiqish» ni bosing."),
         ('smena', "Smena yopilib qolgan", False,
          "Smena yopilmagan — u faqat siz yopganingizda yopiladi. Bu shunchaki 10 daqiqalik harakatsizlik himoyasi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return "To'rtta vaziyat. Har birida o'zingiz nima qilishingizni tanlang."


def sahna(h):
    return [{'tur': 'ekran', 'sarlavha': 'Libosa · kirish ekrani',
             'matn': "Kim kirmoqda?\nRo'yxatdan o'z ismingizni tanlaysiz va PIN kodingizni terasiz. "
                     "Salon logini va paroli qurilmaga bir marta kiritiladi — uni har kuni terish shart emas."}]


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def bilim(h):
    return [
        "PIN — sizning imzoingiz: u bilan qilingan har bir ish sizning nomingizga yoziladi. Shuning uchun PIN hech kimga berilmaydi, "
        "o'z nomingizdan kirib planshetni boshqaga ham bermaysiz. Unutilgan PIN'ni rahbar almashtirib beradi.",
        "PIN ketma-ket 5 marta xato terilsa, kirish 15 daqiqaga to'xtaydi va rahbarga xabar boradi. Rahbar uni Telegramdan darhol "
        "ocha oladi.",
        "Yangi planshet yoki telefon salonga faqat rahbar ruxsati bilan ulanadi: ekranda «Qurilma rahbar ruxsatini kutmoqda» chiqadi, "
        "rahbarga esa Telegramda «Ruxsat / Rad» so'rovi boradi.",
        "10 daqiqa hech narsa bosilmasa, ilova yana PIN so'raydi. Bu xato emas — himoya: qarovsiz planshetda hech kim sizning "
        "nomingizdan ishlamasin.",
    ]


DARS = Dars(
    kod='K1', nomi='Kirish va PIN', yonalish='kirish', personaj='madina',
    sahifa='Kirish ekrani',
    vaziyat="Libosa'da har kim o'z ismi va PIN kodi bilan kiradi. PIN — sizning imzoingiz: tizim har bir zakaz va har bir "
            "so'mni kim yozganini biladi.",
    natija="O'z PIN kodingizni qanday himoyalashni va kirishda nima bo'lsa, nima qilishni bilasiz.",
    xulosa="Uch qoida: PIN hech kimga berilmaydi; planshetdan uzoqlashsangiz, ilovadan chiqasiz; yangi qurilmani faqat rahbar "
           "ochadi. Tizimda har bir amal uni bajargan odamning nomi bilan qoladi.",
    tekshirilgan='2026-11-13 · kod bilan solishtirilgan (ekranda emas — kirish o\'quv salonida ochilmaydi)',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, sahna=sahna, savollar=lambda h: SAVOLLAR,
    ishora="Har savolda o'ylang: tizim shu amalni kimning nomiga yozadi?",
    xp=40,
)
