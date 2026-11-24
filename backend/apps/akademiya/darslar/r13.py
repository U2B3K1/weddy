"""R13 — Bot rahbar uchun. Telegram bot o'quv salonida ishlamaydi (tashqariga xabar chiqmasin), shuning uchun vaziyatlar
orqali. Matnlar kod bilan solishtirilgan (notify/bot_menyu.py): rahbar menyusi — MENYU, «📊 Bugun» — bugun_xabari («💰 Kassa batafsil» — _kassa), «✅ Qarorlar»
— _qaror (chegirma, xarajat, o'tkazma — har biri o'z tugmasi bilan), libos bandligi — kod va sana yoziladi
(«A12 25.11», menyuda tugmasi yo'q), xarajat xabari — finance.services.xarajat_xabar_matni va xarajat_tugmalari."""
from .asos import Dars, faqat_rahbar, savollarni_tekshir

SAVOLLAR = [
    {'matn': "Shahardan tashqaridasiz. Hozir kassada qancha naqd borligini va bugun qancha pul kirganini bilmoqchisiz. Nima qilasiz?",
     'variantlar': [
         ('qongiroq', "Sotuvchiga qo'ng'iroq qilib so'rayman", False,
          "Sotuvchini ishdan chalg'itish shart emas — va u aytgan raqam tizimdagi bilan bir xil bo'lmasligi mumkin. Botda «📊 Bugun» bor."),
         ('kassa', "Botda «📊 Bugun» ni bosaman", True,
          "To'g'ri: bugungi tushum (terminal va o'tkazmalar alohida), kassadagi naqd (hisob bo'yicha) va xarajat — bir xabarda. "
          "Kassa bo'yicha batafsili — xabar ostidagi «💰 Kassa batafsil» tugmasida."),
         ('kechqurun', "Kechqurungi hisobotni kutaman", False,
          "Kutish shart emas: «📊 Bugun» shu daqiqadagi holatni ko'rsatadi."),
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
          "Buning uchun alohida tugma bor: «✅ Qarorlar» — javobsiz qolgan hamma narsani qayta chiqaradi."),
         ('qaror', "«✅ Qarorlar» ni bosaman", True,
          "To'g'ri: chegirma so'rovlari, xarajatlar va «hisobingizga tushdimi?» degan o'tkazmalar — har biri o'z tugmasi bilan qayta keladi."),
         ('tashlab', "Hech narsa — javobsiz qolgani o'zi tasdiqlanadi", False,
          "O'zi tasdiqlanmaydi: chegirma so'rovi javobsiz qolsa, zakaz kutib turadi va oxiri bron bekor bo'ladi."),
     ]},
    {'matn': "Tanishingiz qo'ng'iroq qildi: «A12 libosingiz 25-noyabrga bo'shmi?» Planshet yoningizda yo'q. Nima qilasiz?",
     'variantlar': [
         ('keyin', "«Ertaga aytaman», deyman", False,
          "Mijozni kuttirish shart emas: botga «A12 25.11» deb yozsangiz — javob bir daqiqada."),
         ('libos', "Botga «A12 25.11» deb yozaman", True,
          "To'g'ri: libos kodi (yoki nomi) va sana — bot shu kunga bo'sh yoki bandligini aytadi. Zakazni topish uchun esa uning raqamini yoki mijoz telefonini yozasiz."),
         ('taxmin', "«Bo'sh bo'lsa kerak», deyman", False,
          "Taxmin bilan va'da bermang — libos band chiqsa, noqulay bo'ladi. Botga kod va sanani yozing — aniq javob beradi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return "Siz salonda emassiz, qo'lingizda faqat telefon. To'rtta vaziyat — har birida botdan qanday foydalanishingizni tanlang."


def sahna(h):
    return [{'tur': 'bot', 'sarlavha': 'Libosa bot · rahbar menyusi', 'matn': "Pastdagi tugmalar — salon haqidagi savollaringiz:",
             'tugmalar': ['📊 Bugun', '✅ Qarorlar', '⚙️ Sozlamalar']},
            {'tur': 'bot', 'sarlavha': 'Libosa bot · yangi xabar',
             'matn': "🧾 Madina xarajat kiritdi: Tozalash (ximchistka) — 40 000 so'm (kassadan) · «Zarbof ximchistkaga berildi».",
             'tugmalar': ['Tasdiqlash', 'Rad etish']}]


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def bilim(h):
    return [
        "Botning menyusida uchta tugma bor. «📊 Bugun» — tushum, kassadagi naqd va kun xulosasi bitta xabarda; ostida «💰 Kassa batafsil», «📅 Ertaga» va «🔄 Yangilash».",
        "Qaror talab qiladigan xabar (xarajat, chegirma, o'tkazma) tugmasi bilan keladi: javob — xabar ostidagi tugmani bosish. "
        "Buning uchun salonga borish shart emas.",
        "«✅ Qarorlar» — hali javob berilmagan hamma so'rovlar: har biri o'z tugmasi bilan qayta chiqadi.",
        "Libos bo'shmi — botga libos kodi (yoki nomi) va sanani yozasiz («A12 25.11»), bot shu kunga bo'sh yoki bandligini aytadi. "
        "Zakazni topish — raqamini yoki mijoz telefonini yozasiz. Buning uchun tugma bosish shart emas.",
    ]


DARS = Dars(
    kod='R13', nomi='Bot rahbar uchun', yonalish='rahbar', personaj='nodira',
    sahifa='Telegram bot',
    vaziyat="Rahbar har doim ham salonda o'tirmaydi. Lekin salon to'xtamaydi: sotuvchi chegirma so'raydi, kassadan xarajat qiladi, "
            "mijoz o'tkazma yuboradi. Bularning hammasi telefoningizga keladi — va javobni ham o'sha yerdan berasiz.",
    natija="Salonda bo'lmagan paytda ham kassani ko'rasiz va qarorlarni Telegram botdan berasiz.",
    xulosa="Bot — sizning cho'ntakdagi salon: «📊 Bugun» — holat va kassa, «✅ Qarorlar» — sizni kutayotgan ishlar, "
           "kod va sana yoki zakaz raqamini yozish — mijozga tez javob, «⚙️ Sozlamalar» → «💳 To'lov» — obuna. Qaror talab qiladigan xabarlar "
           "(chegirma, xarajat, o'tkazma, yangi qurilma) tugmasi bilan keladi va ularni o'chirib bo'lmaydi; qolganini "
           "«⚙️ Sozlamalar» da o'zingizga moslaysiz. Bot ishlashi uchun Telegramni ilovada bir marta ulash kerak.",
    tekshirilgan="2026-11-19 · kod bilan solishtirilgan (o'quv salonida bot ishlamaydi)",
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, sahna=sahna, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Har vaziyatda o'ylang: bu savolga javob beradigan tugma menyuda bormi?",
    xp=50,
)
