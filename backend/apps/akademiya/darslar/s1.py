"""S1 — Libos bo'shmi? Mijoz hali zakaz bermayapti, faqat so'rayapti: bandlik tekshiriladi, hech narsa saqlanmaydi.
Javob panelda tanlanadi. Zakaz (mijoz ma'lumoti bilan) — keyingi dars; bu yakundagi xulosada aniq aytiladi."""
from .asos import LIBOSLAR, LIBOSLAR_ROYXATI, Dars, holat_sanalari, kun, mezon, nav, sana_matni, tab, toy_katalogi, tugma


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    return {'dan': dan.isoformat(), 'gacha': gacha.isoformat(), 'liboslar': {k: v.id for k, v in l.items()}}


def topshiriq(h):
    dan, gacha = holat_sanalari(h)
    return (f"Mijoz hozircha faqat so'rayapti: {sana_matni(dan)} kuni olib ketib, {sana_matni(gacha)} kuni qaytarish uchun "
            f"44-o'lchamdagi milliy libos bormi? Shu kunlarga bo'sh liboslarni ko'ring. Bu tekshiruv — zakaz hali yaratilmaydi.")


def savol(h):
    # tartib artikul bo'yicha — to'g'ri javob o'rnidan bilinmaydi; o'lcham va toifa atayin yozilmagan (ilovadan topiladi)
    return {'matn': 'Mijozga qaysi libosni taklif qilasiz?',
            'variantlar': [{'id': k, 'matn': f'{LIBOSLAR[k][0]} · {LIBOSLAR[k][1]}'}
                           for k in sorted(VARIANTLAR, key=lambda k: LIBOSLAR[k][0])]}


# Savolda faqat «Milliy» toifasidagi liboslar: oxirgi qadamda aynan shu ro'yxat yoritiladi — o'quvchi har bir variantni
# ekrandan tekshira oladi (Atlas ro'yxatda yo'q — demak band). Boshqa toifadagi libos ekranda ko'rinmaydi, shuning uchun so'ralmaydi.
VARIANTLAR = ('band', 'boshqa_olcham', 'togri')

XATO = {
    'band': "Atlas shu kunlarga band — uni boshqa mijoz bron qilgan. Shuning uchun u ro'yxatda yo'q.",
    'boshqa_olcham': "Adras bo'sh, lekin 46-o'lcham. Mijozga 44-o'lcham kerak.",
}


def tekshir(m, javob):
    if javob not in VARIANTLAR:
        return [mezon(False, '', 'Avval liboslardan birini tanlang.')]
    return [mezon(javob == 'togri', "To'g'ri: Zarbof — milliy, 44-o'lcham va shu kunlarga bo'sh.", XATO.get(javob, ''))]


def qadamlar(h):
    dan, gacha = holat_sanalari(h)
    return ["Menyuda «Kassa» ni oching va tepadagi bo'limlardan «Yangi zakaz» ni tanlang.",
            f"Kalendarda {sana_matni(dan)} va {sana_matni(gacha)} kunlarini bosing, keyin «Davom etish — liboslarni tanlash».",
            "Tepadagi toifalardan «Milliy» ni, «O'lcham» ro'yxatidan 44 ni tanlang.",
            "Ro'yxatda qolgan libos — shu kunlarga bo'sh va mijozga mos. Uning nomini shu yerda belgilang.",
            "Zakazni saqlamang: mijoz hali qaror qilgani yo'q. Zakaz — keyingi darsda, mijoz ma'lumoti bilan."]


def yol(h):
    dan, gacha = holat_sanalari(h)
    return [nav('Kassa'), tab('Yangi zakaz'), kun(dan, 'olib ketish'), kun(gacha, 'qaytarish'),
            tugma('Davom etish — liboslarni tanlash', "Sanalar tanlandi. «Davom etish — liboslarni tanlash» ni bosing."),
            {'matn': "Ro'yxatda faqat shu kunlarga bo'sh liboslar turibdi. Har birining toifasi va o'lchamiga qarang, "
                     "keyin savolga javob bering.", 'amal': 'kor', 'nishon': LIBOSLAR_ROYXATI}]


def bilim(h):
    return [
        "Ro'yxatda yo'q libos — shu kunlarga band. Bo'shlari ichidan mijoz so'ragan toifa va o'lchamga mos kelganini taklif qilasiz.",
    ]


DARS = Dars(
    kod='S1', nomi="Libos bo'shmi?", yonalish='sotuvchi', personaj='madina',
    sahifa='Kassa → Yangi zakaz',
    vaziyat="Salonga mijoz keldi: shanba kuni to'yi bor. Hali zakaz bermayapti — avval so'rayapti: o'sha kunlarga milliy "
            "libos bormi? Javob berish uchun bandlikni tekshiramiz.",
    natija="Mijoz so'ragan kunlarga qaysi libos bo'shligini bir daqiqada ayta olasiz.",
    xulosa="Siz faqat bandlikni tekshirdingiz: hech narsa saqlanmadi va libos hali band emas — boshqa sotuvchi uni olishi mumkin. "
           "Libos mijozga faqat zakaz bilan biriktiriladi, zakaz esa mijozning telefoni va ismisiz saqlanmaydi. "
           "Keyingi darsda shu yo'lni oxirigacha — mijoz ma'lumoti bilan — o'tamiz.",
    tekshirilgan='2026-11-12 · 1f405b7 dan keyingi ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savol=savol,
    ishora="Liboslar ro'yxati sanaga bog'liq: avval kunlarni tanlang — tizim faqat shu kunlarga bo'sh liboslarni ko'rsatadi.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
