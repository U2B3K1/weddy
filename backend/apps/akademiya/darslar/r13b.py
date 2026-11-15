"""R13B — SMS va integratsiyalar (rahbar). Sozlama → «SMS eslatma» (`sms_eslatma`, `sms_kvitansiya`) va «Integratsiyalar»
(Telegram bot, Eskiz, Click/Payme — Integratsiyalar.jsx) bitta sahifada. SMS Eskiz.uz hisobi bilan yuboriladi; hisob
kiritilmagan bo'lsa faqat jurnalga yoziladi (notify/sms.py). O'quv salonidan SMS umuman ketmaydi (sms.py: `oquv`),
integratsiyalar akademiyada faqat o'qish uchun ochiq (akademiya/host.py)."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

ESLATMA = 'Ertaga olib ketish va qaytarish eslatmasi'
KVITANSIYA = "To'lovdan keyin SMS kvitansiya"

SAVOLLAR = [
    {'matn': "SMS kvitansiya nima uchun kerak?",
     'variantlar': [
         ('reklama', "Mijozga reklama yuborish uchun", False, "Reklama emas: kvitansiya — mijoz bergan pulni tasdiqlovchi xabar."),
         ('nazorat', "Mijoz bergan summa va usul unga darhol keladi — xodim kamroq yozsa, mijoz biladi", True,
          "To'g'ri: «Zakaz #123 uchun 2 000 000 so'm qabul qilindi (naqd)». Xodim boshqa summa yoki usul yozsa, mijoz darhol ko'radi."),
         ('chek', "Fiskal chek o'rniga", False, "Fiskal chekni almashtirmaydi — bu faqat mijozga ma'lumot."),
     ]},
    {'matn': "Ikkala SMS ni yoqdingiz, lekin mijozlarga hech narsa kelmayapti. Sababi nima bo'lishi mumkin?",
     'variantlar': [
         ('eskiz', "Eskiz.uz hisobi ulanmagan — «Integratsiyalar» da kiritiladi", True,
          "To'g'ri: SMS Eskiz orqali, uning balansidan yuboriladi. Hisob kiritilmaguncha SMS lar faqat jurnalga yoziladi."),
         ('tg', "Mijozning Telegrami ulanmagan", False, "SMS Telegramga bog'liq emas — u Eskiz.uz orqali telefon raqamga boradi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return ("Mijozlar olib ketish kunini unutib qo'yishyapti, ba'zan to'langan summa bo'yicha tortishuv chiqyapti. Ikkala SMS ni "
            "yoqing: ertangi eslatma va to'lovdan keyin kvitansiya. Keyin shu sahifadagi «Integratsiyalar» ni ko'rib chiqing.")


def tekshir(m, javob=None):
    s = sozlama(m.salon)
    return [
        mezon(s.sms_eslatma, "Ertangi eslatma SMS i yoqildi.", "«Ertangi eslatma» hali o'chiq."),
        mezon(s.sms_kvitansiya, "SMS kvitansiya yoqildi.", "«SMS kvitansiya» hali o'chiq."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «SMS eslatma» bo'limiga kiring.",
            "Ikkala almashtirgichni yoqing va pastdagi «Saqlash» ni bosing.",
            "Shu sahifaning tepasidagi «Integratsiyalar» ni ko'rib chiqing: SMS uchun «Eskiz SMS» ulangan bo'lishi kerak."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('SMS eslatma'),
            {'matn': "Birinchisi — ertangi eslatma: mijozga kechqurun «ertaga libosni olib ketasiz / qaytarasiz». Yoqing.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': ESLATMA}, 'tayyor': {'css': '.sozlama-saqlash'}},
            {'matn': "Ikkinchisi — to'lovdan keyin kvitansiya. Uni ham yoqing.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': KVITANSIYA}},
            SAQLASH,
            {'matn': "Endi «Integratsiyalar»: Telegram bot, Eskiz SMS, Click va Payme shu yerda ulanadi. O'quv salonida ular faqat "
                     "ko'rish uchun. Qarab chiqing va savollarga javob bering.", 'amal': 'kor',
             'nishon': {'css': '#soz-integratsiyalar'}}]


def bilim(h):
    return [
        "SMS kvitansiya — to'lov qabul qilingach mijozga boradigan xabar: summa va to'lov usuli. Xodim boshqa summa yoki usul "
        "yozsa, mijoz buni darhol ko'radi.",
        "SMS lar Eskiz.uz orqali, uning balansidan yuboriladi. Eskiz hisobi «Integratsiyalar» da kiritilmagan bo'lsa, SMS ketmaydi — "
        "faqat jurnalga yoziladi.",
    ]


DARS = Dars(
    kod='R13B', nomi='SMS va integratsiyalar', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → SMS eslatma · Integratsiyalar',
    vaziyat="Ba'zi mijoz Telegramdan foydalanmaydi, lekin SMS ni hamma o'qiydi. Eslatma va kvitansiya SMS bilan ketsa, mijoz "
            "olib ketish kunini unutmaydi va bergan puli qanday yozilganini o'zi ko'radi.",
    natija="Mijozga SMS eslatma va kvitansiyani yoqasiz va ular ishlashi uchun nima kerakligini bilasiz.",
    xulosa="Ikkala SMS yoqildi. Ular haqiqatan ketishi uchun «Integratsiyalar» → «Eskiz SMS» da Eskiz.uz hisobi kiritilgan "
           "bo'lishi kerak — har SMS uning balansidan. Yuborilganlar shu bo'limning pastida ko'rinadi (yetkazildi / xato). "
           "O'quv salonidan SMS umuman yuborilmaydi — buni haqiqiy salonda bir marta sozlang.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="SMS va integratsiyalar «Ko'rinish va xabarlar» guruhida, bitta sahifada.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
