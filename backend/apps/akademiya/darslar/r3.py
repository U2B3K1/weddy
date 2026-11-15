"""R3 — Kirishni Telegramda tasdiqlash (rahbar). Rahbar kirishi va yangi qurilma bot orqali tasdiqlanadi.
O'quv salonida Telegram ulanmaydi, shuning uchun haqiqiy bot xabarlari ko'rsatilib, vaziyat so'raladi.
Xabar matnlari notify/services.py dagi bilan bir xil (kirish_kodi_yubor, qurilma_kutmoqda_xabari); qoidalar:
kod 5 daqiqa, shu qurilmada 3 kun faol bo'lsa qayta so'ralmaydi (RAHBAR_FAOLSIZLIK)."""
from .asos import Dars, faqat_rahbar, savollarni_tekshir

SAVOLLAR = [
    {'matn': "Salondasiz, PIN kodni terdingiz — ilova kutyapti va Telegramga birinchi xabar keldi. Nima qilasiz?",
     'variantlar': [
         ('ruxsat', "«Ruxsat berish» ni bosaman", True,
          "To'g'ri: tugma bosilishi bilan ilova o'zi kiradi, kodni terish ham shart emas."),
         ('aytaman', "Kodni sotuvchiga aytaman, u terib qo'yadi", False,
          "Kod hech kimga berilmaydi — u sizning nomingizdan kirish kaliti. O'zingiz «Ruxsat berish» ni bosing."),
         ('kutaman', "Xabarga tegmayman, ilova o'zi kiradi", False,
          "O'zi kirmaydi: so'rov 5 daqiqa kutadi va bekor bo'ladi. «Ruxsat berish» ni bosish kerak."),
     ]},
    {'matn': "Uydasiz, ilovaga kirmagansiz. Telegramga xuddi shu «kirish so'raldi» xabari keldi. Nima qilasiz?",
     'variantlar': [
         ('ruxsat', "«Ruxsat berish» ni bosaman — balki xodimlardan biriga kerakdir", False,
          "Bu eng xavfli tanlov: kimdir sizning PIN kodingiz bilan rahbar bo'lib kirmoqchi. Ruxsat bersangiz, u hamma narsani "
          "ko'radi va o'zgartira oladi."),
         ('emas', "«Bu men emas» ni bosaman va PIN kodimni almashtiraman", True,
          "To'g'ri: kirish rad etiladi. So'rov kelganining o'zi kimdir PIN'ingizni bilishini anglatadi — uni darhol almashtiring."),
         ('etibor', "E'tibor bermayman — 5 daqiqada o'zi o'chadi", False,
          "So'rov o'chadi, lekin muammo qoladi: kimdir PIN kodingizni biladi. «Bu men emas» ni bosib, PIN'ni almashtiring."),
     ]},
    {'matn': "Ikkinchi xabar keldi: yangi qurilma ruxsat so'rayapti. Salonga yangi planshet olinmagan, xodimlar ham "
             "so'ramagan. Nima qilasiz?",
     'variantlar': [
         ('ruxsat', "«Ruxsat» ni bosaman", False,
          "Ruxsat bersangiz, begona qurilma saloningizga kiradi. Notanish qurilmaga hech qachon ruxsat berilmaydi."),
         ('rad', "«Rad» ni bosaman va salon parolini almashtiraman", True,
          "To'g'ri: so'rov kelgan bo'lsa, kimdir salon parolini biladi. Uni Sozlama → «Qurilmalar va parol» da almashtirasiz."),
         ('kutaman', "Javob bermayman", False,
          "Qurilma kutishda qolaveradi va so'rov takrorlanadi. «Rad» ni bosing va salon parolini almashtiring."),
     ]},
    {'matn': "Bugun odatdagi planshetdan kirdingiz — Telegram umuman so'ralmadi. Nega?",
     'variantlar': [
         ('buzuq', "Bot ishlamayapti", False,
          "Bot ishlayapti. Shu qurilmada oxirgi 3 kun ichida tasdiqlanib kirgan bo'lsangiz, tizim qayta so'ramaydi."),
         ('uch', "Shu qurilmada oxirgi 3 kun ichida tasdiqlanib kirganman", True,
          "To'g'ri: har kuni tasdiqlash shart emas. 3 kun kirmasangiz yoki boshqa qurilmadan kirsangiz — yana so'raladi."),
         ('ochiq', "Himoya o'chirilgan", False,
          "Himoya o'chirilmagan: u faqat siz Telegramni uzganingizda o'chadi. Bu qurilma yaqinda tasdiqlangan, xolos."),
     ]},
]


def urug(m):
    return {'ism': m.xodim.ism}


def topshiriq(h):
    return "Avval botdan keladigan ikki xabarni o'qing, keyin to'rtta vaziyatda nima qilishingizni tanlang."


def sahna(h):
    return [
        {'tur': 'bot', 'sarlavha': 'Libosa boti · kirish tasdig\'i',
         'matn': f"🔐 Libosa: «Samsung planshet» qurilmasidan {h.get('ism') or 'rahbar'} nomidan kirish so'raldi.\n"
                 "Siz bo'lsangiz — «Ruxsat berish»ni bosing, ilova o'zi kiradi.\n\n"
                 "Yoki ilovada kirish kodi: 483920\n5 daqiqa amal qiladi. Hech kimga bermang.",
         'tugmalar': ['✅ Ruxsat berish', '❌ Bu men emas']},
        {'tur': 'bot', 'sarlavha': 'Libosa boti · yangi qurilma',
         'matn': "Yangi qurilma ruxsat so'ramoqda:\nChrome · Android · bugun 09:40",
         'tugmalar': ['✅ Ruxsat', '❌ Rad']},
    ]


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def bilim(h):
    return [
        "Rahbar kirishi ikki bosqichli: PIN'dan keyin Telegramga «kirish so'raldi» xabari keladi. Kirayotgan o'zingiz bo'lsangiz — "
        "«Ruxsat berish»: ilova o'zi kiradi.",
        "O'zingiz kirmayotgan paytda shunday xabar kelsa — kimdir PIN kodingizni biladi. «Bu men emas» ni bosasiz va PIN'ni "
        "almashtirasiz.",
        "Yangi qurilma so'rovi ham shunday: o'zingiz ulamagan bo'lsangiz — «Rad» va salon parolini almashtirasiz "
        "(Sozlama → «Qurilmalar va parol»).",
        "Tasdiq har kuni so'ralmaydi: shu qurilmada oxirgi 3 kun ichida tasdiqlab kirgan bo'lsangiz, PIN yetarli.",
    ]


DARS = Dars(
    kod='R3', nomi="Kirishni Telegramda tasdiqlash", yonalish='rahbar', personaj='nodira',
    sahifa='Telegram · Libosa boti',
    vaziyat="Rahbar hamma narsani ko'radi: pul, hisobotlar, sozlamalar. Shuning uchun rahbar kirishi ikki bosqichli — PIN'dan "
            "keyin Telegramda tasdiqlaysiz. Salonga yangi qurilma ham faqat sizning ruxsatingiz bilan kiradi.",
    natija="Botdagi kirish so'rovlariga to'g'ri javob bera olasiz va begona kirishni to'xtata olasiz.",
    xulosa="Qoida oddiy: so'rovni o'zingiz boshlagan bo'lsangiz — ruxsat; boshlamagan bo'lsangiz — rad va parolni almashtirish "
           "(PIN — o'zingizniki, salon paroli — Sozlama → «Qurilmalar va parol»). Bu himoya faqat Telegram ulangan bo'lsa "
           "ishlaydi: ulanmagan rahbar faqat PIN bilan kiradi, yangi qurilmani esa o'sha qurilmada PIN bilan tasdiqlaydi.",
    tekshirilgan='2026-11-13 · kod bilan solishtirilgan (haqiqiy Telegramda sinalmagan)',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, sahna=sahna, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Har safar o'zingizdan so'rang: bu kirishni hozir men boshladimmi?",
    xp=60,
)
