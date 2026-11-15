"""R8B — Avans qaytarish qoidasi (rahbar). Sozlama → «Avans qaytarish» (Sozlamalar.jsx `qaytarish`): jadval
`qaytarish_qoidasi` ([[kun, foiz], ...], standart [[30, 100], [7, 50], [0, 0]]); oxirgi qator — «N kundan kam».
Bekor qilishda tizim qolgan kunga qarab foizni o'zi topadi (orders/changes.qaytariladigan_foiz, bekor_hisobi); rahbar bekor
qilayotganda boshqa foiz kirita oladi (Zakazlar.jsx BekorForma, `qaytariladigan_foiz_override`)."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, som, sozlama_qatori

YANGI = 30
QOIDA = [[30, 100], [7, 50], [0, YANGI]]
AVANS = 1_000_000

SAVOLLAR = [
    {'matn': f"Yangi qoida bo'yicha: mijoz {som(AVANS)} avans bergan va to'yiga 3 kun qolganda zakazni bekor qildi. Unga qancha qaytadi?",
     'variantlar': [
         ('nol', "Hech narsa", False, f"Bu eski qoida edi. Endi 7 kundan kam qolganda ham {YANGI}% qaytadi: {som(AVANS * YANGI // 100)}."),
         ('togri', som(AVANS * YANGI // 100), True,
          f"To'g'ri: 3 kun — «7 kundan kam» qatori, {YANGI}%. Bekor qilishda tizim summani o'zi ko'rsatadi."),
         ('yarmi', som(AVANS // 2), False, "50% — 7–29 kun qolganda. 3 kun — oxirgi qator."),
     ]},
    {'matn': "Doimiy mijozingiz kasal bo'lib qoldi, to'y qoldirildi. Qoida bo'yicha 30% qaytadi, siz esa 80% qaytarmoqchisiz. Nima qilasiz?",
     'variantlar': [
         ('qoida', "Qoidani 80% ga o'zgartirib, keyin qaytaraman", False,
          "Unda hamma mijozga 80% qaytib ketadi. Bitta zakaz uchun qoidani o'zgartirish shart emas."),
         ('qolda', "Zakazni o'zim bekor qilaman va «Qaytariladigan foiz» ga 80 yozaman", True,
          "To'g'ri: rahbar bekor qilayotganda qoidadan boshqa foiz kirita oladi — faqat shu zakaz uchun. Sotuvchida bu maydon yo'q."),
         ('naqd', "Qoida bo'yicha qaytaraman, ustiga naqd qo'shib beraman", False,
          "Kassadan yozilmagan pul chiqib ketadi va kassa farq qiladi. Foizni bekor qilishning o'zida qo'ying."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Mijozlar shikoyat qilyapti: to'yga bir hafta qolmay bekor qilsa, avansning hammasi kuyib ketadi. Qaror qildingiz: "
            f"7 kundan kam qolganda ham avansning {YANGI}% qaytarilsin. Qoidani o'zgartiring.")


def tekshir(m, javob=None):
    q = sozlama(m.salon).qaytarish_qoidasi
    return [
        mezon(q == QOIDA, f"Qoida saqlandi: 30+ kun — 100%, 7–29 kun — 50%, 7 kundan kam — {YANGI}%.",
              f"Qoida hali o'zgarmagan yoki boshqacha: {q}. Faqat oxirgi qatorni {YANGI}% qiling va «Saqlash» ni bosing."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Avans qaytarish» bo'limiga kiring.",
            f"Jadvalning oxirgi qatorida («7 kundan kam») foizni {YANGI} qiling.",
            "Pastdagi «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Avans qaytarish'),
            {'matn': f"Jadval: olib ketishgacha qancha kun qolsa, avansning qancha foizi qaytadi. Oxirgi qatorda («7 kundan kam») "
                     f"0% turibdi. Uni {YANGI} qiling.", 'amal': 'yoz',
             'nishon': {'css': 'input', 'label': '3-qoida: qaytariladigan foiz'}, 'kutilgan': f'raqam:{YANGI}'},
            SAQLASH]


def bilim(h):
    return [
        "Bekor qilishda tizim kerakli qatorni o'zi topadi va qaytadigan summani ko'rsatadi: avans × shu qatordagi foiz.",
        "Alohida holat uchun qoidani o'zgartirish shart emas: zakazni rahbar o'zi bekor qilsa, «Qaytariladigan foiz» ga boshqa son "
        "yoza oladi — faqat shu zakaz uchun. Sotuvchida bu maydon yo'q.",
    ]


DARS = Dars(
    kod='R8B', nomi='Avans qaytarish qoidasi', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Avans qaytarish',
    vaziyat="Zakaz bekor bo'lsa, avansdan qanchasi qaytishini sotuvchi emas, qoida hal qiladi. Qoida — sizniki: uni salon "
            "siyosatiga qarab bir marta sozlaysiz, u shartnomada ham chiqadi.",
    natija="Avans qaytarish qoidasini o'zgartirasiz va alohida holatda qoidadan chetga chiqishni bilasiz.",
    xulosa=f"Yangi qoida faqat bundan keyin yaratiladigan zakazlarga qo'llanadi — eski zakazlar o'z qoidasi bilan qoladi. "
           "Shu bo'limda yana ikki tanlov bor: «Qoida nimaga qo'llanadi» (faqat avansga yoki hamma to'langan summaga) va «Avans "
           "miqdori» (avans — birinchi to'lov yoki zakazning foizi). Bekor qilishda tizim summani o'zi hisoblab ko'rsatadi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Jadvalning har qatori: «kamida shuncha kun qolsa — shuncha foiz qaytadi». Oxirgi qator — qolgan hamma holat.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
