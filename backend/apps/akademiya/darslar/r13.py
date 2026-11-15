"""R13 — Bot rahbar uchun. Telegram bot o'quv salonida ishlamaydi (tashqariga xabar chiqmasin), shuning uchun vaziyatlar
orqali. Matnlar kod bilan solishtirilgan (notify/bot_menyu.py): rahbar menyusi — AMALLAR, «💰 Kassa» — _kassa, «✅ Qaror
kutmoqda» — _qaror (chegirma, xarajat, o'tkazma — har biri o'z tugmasi bilan), «👗 Libos bo'shmi?» — LIBOS_YORDAM
(«A12 25.11»), xarajat xabari — finance.services.xarajat_xabar_matni va xarajat_tugmalari."""
from .asos import Dars, faqat_rahbar, savollarni_tekshir

SAVOLLAR = [
    {'matn': "Shahardan tashqaridasiz. Hozir kassada qancha naqd borligini va bugun qancha pul kirganini bilmoqchisiz. Nima qilasiz?",
     'variantlar': [
         ('qongiroq', "Sotuvchiga qo'ng'iroq qilib so'rayman", False,
          "Sotuvchini ishdan chalg'itish shart emas — va u aytgan raqam tizimdagi bilan bir xil bo'lmasligi mumkin. Botda «💰 Kassa» bor."),
         ('kassa', "Botda «💰 Kassa» ni bosaman", True,
          "To'g'ri: kassadagi naqd (hisob bo'yicha), bugungi naqd tushum, terminal va o'tkazmalar, xarajat — bir xabarda. "
          "Kunning to'liq xulosasi — «📊 Bugun» da."),
         ('kechqurun', "Kechqurungi hisobotni kutaman", False,
          "Kutish shart emas: «💰 Kassa» tugmasi shu daqiqadagi holatni ko'rsatadi."),
     ]},
    {'matn': "Botga yuqoridagi xabar keldi: sotuvchi kassadan xarajat yozgan. Chekining rasmini ko'rdingiz — hammasi to'g'ri. Nima qilasiz?",
     'variantlar': [
         ('ilova', "Salonga borib, ilovadan tasdiqlayman", False,
          "Borish shart emas: xabarning ostidagi «Tasdiqlash» tugmasi ilovadagi bilan bir xil ishlaydi."),
         ('tugma', "Xabar ostidagi «Tasdiqlash» ni bosaman", True,
          "To'g'ri: qaror shu zahoti yoziladi. Ilovada ham, botda ham — qaysi birida birinchi bossangiz, o'sha hisoblanadi."),
         ('yozaman', "Botga «ok, tasdiqlayman» deb yozaman", False,
          "Bot matnli javobni qaror deb tushunmaydi. Qaror faqat xabar ostidagi tugma bilan beriladi."),
     ]},
    {'matn': "Kun davomida bir nechta so'rov keldi. Qaysi biriga javob berganingizni eslay olmayapsiz. Nima qilasiz?",
     'variantlar': [
         ('varaq', "Chatni yuqoriga varaqlab, har birini qidiraman", False,
          "Buning uchun alohida tugma bor: «✅ Qaror kutmoqda» — javobsiz qolgan hamma narsani qayta chiqaradi."),
         ('qaror', "«✅ Qaror kutmoqda» ni bosaman", True,
          "To'g'ri: chegirma so'rovlari, xarajatlar va «hisobingizga tushdimi?» degan o'tkazmalar — har biri o'z tugmasi bilan qayta keladi."),
         ('tashlab', "Hech narsa — javobsiz qolgani o'zi tasdiqlanadi", False,
          "O'zi tasdiqlanmaydi: chegirma so'rovi javobsiz qolsa, zakaz kutib turadi va oxiri bron bekor bo'ladi."),
     ]},
    {'matn': "Tanishingiz qo'ng'iroq qildi: «A12 libosingiz 25-noyabrga bo'shmi?» Planshet yoningizda yo'q. Nima qilasiz?",
     'variantlar': [
         ('keyin', "«Ertaga aytaman», deyman", False,
          "Mijozni kuttirish shart emas: botda «👗 Libos bo'shmi?» bor — javob bir daqiqada."),
         ('libos', "Botda «👗 Libos bo'shmi?» ni bosib, «A12 25.11» deb yozaman", True,
          "To'g'ri: libos kodi (yoki nomi) va sana — bot shu kunga bo'sh yoki bandligini aytadi. Zakazni esa «🔍 Zakaz qidirish» topadi."),
         ('taxmin', "«Bo'sh bo'lsa kerak», deyman", False,
          "Taxmin bilan va'da bermang — libos band chiqsa, noqulay bo'ladi. «👗 Libos bo'shmi?» aniq javob beradi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return "Siz salonda emassiz, qo'lingizda faqat telefon. To'rtta vaziyat — har birida botdan qanday foydalanishingizni tanlang."


def sahna(h):
    return [{'tur': 'bot', 'sarlavha': 'Libosa bot · rahbar menyusi', 'matn': "Pastdagi tugmalar — salon haqidagi savollaringiz:",
             'tugmalar': ['📊 Bugun', '💰 Kassa', '✅ Qaror kutmoqda', '📅 Ertaga', "💳 To'lov", '⚙️ Sozlamalar',
                          '🔍 Zakaz qidirish', "👗 Libos bo'shmi?"]},
            {'tur': 'bot', 'sarlavha': 'Libosa bot · yangi xabar',
             'matn': "🧾 Madina xarajat kiritdi: Tozalash (ximchistka) — 40 000 so'm (kassadan) · «Zarbof ximchistkaga berildi».",
             'tugmalar': ['Tasdiqlash', 'Rad etish']}]


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def bilim(h):
    return [
        "Botning menyusida tugmalar bor. «💰 Kassa» — kassadagi naqd va bugungi tushum; «📊 Bugun» — kunning to'liq xulosasi.",
        "Qaror talab qiladigan xabar (xarajat, chegirma, o'tkazma) tugmasi bilan keladi: javob — xabar ostidagi tugmani bosish. "
        "Buning uchun salonga borish shart emas.",
        "«✅ Qaror kutmoqda» — hali javob berilmagan hamma so'rovlar: har biri o'z tugmasi bilan qayta chiqadi.",
        "«👗 Libos bo'shmi?» — libos kodi (yoki nomi) va sanani yozasiz, bot shu kunga bo'sh yoki bandligini aytadi. "
        "«🔍 Zakaz qidirish» esa zakazni topadi.",
    ]


DARS = Dars(
    kod='R13', nomi='Bot rahbar uchun', yonalish='rahbar', personaj='nodira',
    sahifa='Telegram bot',
    vaziyat="Rahbar har doim ham salonda o'tirmaydi. Lekin salon to'xtamaydi: sotuvchi chegirma so'raydi, kassadan xarajat qiladi, "
            "mijoz o'tkazma yuboradi. Bularning hammasi telefoningizga keladi — va javobni ham o'sha yerdan berasiz.",
    natija="Salonda bo'lmagan paytda ham kassani ko'rasiz va qarorlarni Telegram botdan berasiz.",
    xulosa="Bot — sizning cho'ntakdagi salon: «📊 Bugun» va «💰 Kassa» — holat, «✅ Qaror kutmoqda» — sizni kutayotgan ishlar, "
           "«👗 Libos bo'shmi?» va «🔍 Zakaz qidirish» — mijozga tez javob, «💳 To'lov» — obuna. Qaror talab qiladigan xabarlar "
           "(chegirma, xarajat, o'tkazma, yangi qurilma) tugmasi bilan keladi va ularni o'chirib bo'lmaydi; qolganini "
           "«⚙️ Sozlamalar» da o'zingizga moslaysiz. Bot ishlashi uchun Telegramni ilovada bir marta ulash kerak.",
    tekshirilgan="2026-11-14 · kod bilan solishtirilgan (o'quv salonida bot ishlamaydi)",
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, sahna=sahna, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Har vaziyatda o'ylang: bu savolga javob beradigan tugma menyuda bormi?",
    xp=50,
)
