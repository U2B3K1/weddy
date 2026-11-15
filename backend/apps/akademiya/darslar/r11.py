"""R11 — Sanoq (rahbar). Sanoqni rahbar boshlaydi va yakunlaydi (LibosSanogi.jsx → catalog/sanoq.py): javondagi buyumlar
belgilanadi, yakunda «salonda bo'lishi kerak edi, lekin yo'q» va «tizimda mijozda, lekin javonda» ro'yxatlari chiqadi.
Darsda to'rt libosdan uchtasi topiladi — bittasi «yo'q» bo'lib chiqadi. Xodimning ishtiroki — S12."""
from apps.catalog.models import Sanoq, SanoqQatori

from .asos import LIBOSLAR, TASDIQ_OYNASI, Dars, faqat_rahbar, katalog, mezon, nav, savollarni_tekshir, tab, tasdiq

BOR = [LIBOSLAR[k] for k in ('band', 'boshqa_olcham', 'togri')]  # M-001 Atlas, M-002 Adras, M-003 Zarbof
YOQ = LIBOSLAR['boshqa_toifa']                                   # O-001 Klassik — javonda yo'q

SAVOLLAR = [
    {'matn': f"Natijada «Yo'q (1)»: {YOQ[0]} {YOQ[1]}. Bu nimani anglatadi va birinchi navbatda nima qilasiz?",
     'variantlar': [
         ('chiqar', "Libos yo'qolgan — darhol hisobdan chiqaraman", False,
          "Shoshilmang: «yo'q» — hali «yo'qolgan» degani emas. Avval sababini aniqlang, hisobdan chiqarish — oxirgi qadam."),
         ('surish', "Tizimda u salonda turishi kerak edi: xodimlardan so'rayman, oxirgi zakazini va ta'mir-tozalashni tekshiraman", True,
          "To'g'ri: ko'pincha libos zakazsiz berib yuborilgan, tozalashga ketgan yoki boshqa javonda bo'ladi. Shuni aniqlash kerak."),
         ('kutaman', "Hech narsa — keyingi sanoqda topilib qolar", False,
          "Kutgan sari izini topish qiyinlashadi. Sanoqning ma'nosi — yo'q libosni shu kunning o'zida surishtirish."),
     ]},
    {'matn': "Boshqa sanoqda natija shunday chiqdi: «Tizimda mijozda, lekin javonda (1)». Bu nima?",
     'variantlar': [
         ('ortiq', "Salonda bitta ortiqcha libos paydo bo'lgan", False,
          "Libos ortiqcha emas — u qaytgan, lekin qaytarish tizimga yozilmagan. Zakaz hamon «mijozda» turibdi."),
         ('kiritilmagan', "Libos qaytgan, lekin qaytarish tizimga kiritilmagan — zakazni ochib rasmiylashtirish kerak", True,
          "To'g'ri: garov qaytarilganmi, jarima bo'lganmi — bular ham yozilmagan. Zakazni ochib, qaytarishni rasmiylashtiring."),
         ('xato', "Sanoqdagi xato — e'tibor bermasa ham bo'ladi", False,
          "Bu xato emas, signal: libos javonda, tizim esa uni mijozda deb biladi — demak qaytarish yozilmagan."),
     ]},
]


def urug(m):
    l = katalog(m)
    return {'yoq': l['boshqa_toifa'].id}


def topshiriq(h):
    borlar = ', '.join(f'{a} {n}' for a, n, _, _ in BOR)
    return (f"Oy oxiri — liboslarni sanaymiz. Sanoqni boshlang. Javonda uchta libos bor: {borlar}. Ularni belgilang. "
            f"{YOQ[0]} {YOQ[1]} javonda yo'q — uni belgilamang. Keyin sanoqni yakunlang.")


def tekshir(m, javob=None):
    s = Sanoq.objects.filter(salon=m.salon).order_by('-id').first()
    if not s:
        return [mezon(False, '', "Sanoq hali boshlanmagan.")]
    if not s.yakunlangan:
        return [mezon(False, '', "Sanoq hali yakunlanmagan — natija faqat yakunlangach chiqadi.")]
    topilmagan = set(SanoqQatori.objects.filter(salon=m.salon, sanoq=s, topildi=False).values_list('libos_id', flat=True))
    return [
        mezon(s.topilgan == len(BOR), f"Javondagi {len(BOR)} ta libos belgilandi.",
              f"{s.topilgan} ta libos belgilangan — javonda {len(BOR)} ta bor edi."),
        mezon(topilmagan == {m.holat['yoq']}, f"Natija to'g'ri: yo'q — {YOQ[0]} {YOQ[1]}.",
              f"Natija noto'g'ri chiqdi: yo'q bo'lib faqat {YOQ[0]} {YOQ[1]} chiqishi kerak edi. Ko'rmagan libosni belgilamang, "
              "ko'rganini qoldirmang. «Qayta boshlash» ni bosing."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Liboslar» ni oching va «Sanoq» bo'limiga o'ting. «Sanoqni boshlash» ni bosing.",
            "«Hali topilmaganlar» ro'yxatida javondagi uchta libosning har biri uchun «Topildi» ni bosing.",
            f"{YOQ[0]} {YOQ[1]} ni belgilamang — u javonda yo'q.",
            "Pastdagi «Sanoqni yakunlash» ni bosing va tasdiqlang."]


def belgila(artikul, nomi):
    return {'matn': f"{artikul} {nomi} javonda bor — qatoridagi «Topildi» ni bosing.", 'amal': 'bos',
            'nishon': {'css': '.sanoq-q', 'ichida': artikul}, 'ichki': {'css': 'button', 'matn': 'Topildi'},
            'tayyor': {'css': '.sanoq-oxirgi-q', 'ichida': artikul}}


def yol(h):
    return [nav('Liboslar'), tab('Sanoq'),
            {'matn': "«Sanoqni boshlash» ni bosing — tizim hozir salonda bo'lishi kerak bo'lgan liboslar ro'yxatini tuzadi.", 'amal': 'bos',
             'nishon': {'css': 'button.bosh-tugma', 'ichida': 'Sanoqni boshlash'}, 'tayyor': {'css': '.sanoq-kiritish'}},
            *[belgila(a, n) for a, n, _, _ in BOR],
            {'matn': f"{YOQ[0]} {YOQ[1]} javonda yo'q — uni belgilamaymiz. «Sanoqni yakunlash» ni bosing.", 'amal': 'bos',
             'nishon': {'css': '.sanoq-yakun button.bosh-tugma'}, 'tayyor': TASDIQ_OYNASI},
            tasdiq('Ha, yakunlash', "Tizim ogohlantiryapti: 1 ta buyum topilmagan, yakunlangan sanoqqa qayta belgilab bo'lmaydi. "
                                    "«Ha, yakunlash» ni bosing.", tayyor={'css': '.r2-sanoq-natija'})]


def bilim(h):
    return [
        "Natijadagi «Yo'q» — tizim bo'yicha salonda turishi kerak, lekin javonda topilmagan libos. Bu darhol «yo'qoldi» degani emas: "
        "ko'pincha u zakazsiz berilgan, tozalashga ketgan yoki boshqa javonda bo'ladi. Avval xodimlardan so'raladi, oxirgi zakazi va "
        "ta'mir-tozalash tekshiriladi.",
        "«Tizimda mijozda, lekin javonda» — buning aksi: libos qaytgan, lekin qaytarish tizimga kiritilmagan. Zakazni ochib, "
        "qaytarishni rasmiylashtirish kerak.",
    ]


DARS = Dars(
    kod='R11', nomi='Sanoq', yonalish='rahbar', personaj='nodira',
    sahifa='Liboslar → Sanoq',
    vaziyat="Tizimda yigirmata libos «salonda» deb turibdi. Javonda ham yigirmatami? Libos zakazsiz berib yuborilgan, tozalashdan "
            "qaytmagan yoki shunchaki yo'qolgan bo'lishi mumkin — buni faqat sanoq ko'rsatadi.",
    natija="Sanoqni boshlab, yakunlaysiz va natijadagi «yo'q» libos bilan nima qilishni bilasiz.",
    xulosa=f"Sanoq yakunlandi: {len(BOR)} ta libos joyida, {YOQ[0]} {YOQ[1]} — yo'q. Natija sizga Telegramda ham boradi va Dashboard'da "
           "«Oxirgi sanoq» qatorida ko'rinadi. Sanoqni xodimlar bilan birga o'tkazing — bir necha kishi bir vaqtda belgilay oladi; "
           "tasodifan boshlangan sanoqni «Bekor qilish» mumkin.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Sanoqda faqat qo'lingiz bilan ushlab ko'rgan libos belgilanadi. Belgilanmagani yakunda «yo'q» bo'lib chiqadi.",
    qadamlar=qadamlar, yol=yol, xp=70,
)
