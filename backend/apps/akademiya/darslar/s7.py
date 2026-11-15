"""S7 — Chegirma so'rash. Ikki yo'l (Zakazlar.jsx ChegirmaForma, orders/discounts.py): tayyor chegirma — bir bosishda,
tasdiqsiz (tayyor_chegirma_qollash); ro'yxatda yo'q chegirma — rahbar tasdig'iga ketadi, zakaz «Chegirma tasdig'i
kutilmoqda» holatiga o'tadi va qaror kelguncha avans olinmaydi (chegirma_sorash, cash.services.tolov_qabul).
Amalda birinchisi bajariladi, ikkinchisi — vaziyatli savollar bilan."""
from apps.orders.models import ChegirmaSorovi, TayyorChegirma, Zakaz
from apps.orders.services import zakaz_yaratish

from .asos import (BOSHQA_AMALLAR, IJARA, MIJOZ_FIO, MIJOZ_TELEFON, TASDIQ_OYNASI, Dars, amal_bolimi, mezon, nav,
                   savollarni_tekshir, som, tasdiq, toy_katalogi, zakazni_och)

NOMI, FOIZ = 'Doimiy mijoz', 10
CHEGIRMA = IJARA * FOIZ // 100

SAVOLLAR = [
    {'matn': "Boshqa mijoz 20% chegirma so'rayapti — libosda kichik nuqson bor ekan. Tayyor chegirmalar ichida bunday yo'q. Nima qilasiz?",
     'variantlar': [
         ('ozim', "Narxni og'zaki kelishib, kassaga kamroq pul yozaman", False,
          "Unda zakazdagi narx bilan olingan pul mos kelmaydi: qoldiq «to'lanmagan» bo'lib turadi va rahbar sababini so'raydi."),
         ('soray', "«Boshqa chegirma» ga 20 yozib, sababini tanlayman va «Rahbardan so'rash» ni bosaman", True,
          "To'g'ri: so'rov rahbarga ilovada va Telegramda boradi. U tasdiqlasa, narx o'zi o'zgaradi."),
         ('yoq', "«Chegirma yo'q» deb javob beraman", False,
          "Rad etishga shoshilmang: ro'yxatda yo'q chegirmani rahbardan so'rash mumkin — bir daqiqalik ish."),
     ]},
    {'matn': "So'rov rahbarga ketdi. Mijoz esa hoziroq avans bermoqchi. Nima bo'ladi?",
     'variantlar': [
         ('olaman', "Avansni olib qo'yaveraman", False,
          "Tizim olmaydi: narx hali aniq emas. Rahbar qaror qilguncha avans qabul qilinmaydi."),
         ('kutadi', "Rahbar qaror qilguncha avans olinmaydi — javob kelishi bilan olaman", True,
          "To'g'ri: tasdiq yoki rad javobi sizga qo'ng'iroqchada va Telegramda keladi. Kutishni istamasangiz, so'rovni qaytarib olib, "
          "chegirmasiz narxda davom etish mumkin."),
         ('bekor', "Zakaz bekor bo'ladi", False, "Zakaz bekor bo'lmaydi — u rahbar qarorini kutib turadi."),
     ]},
]


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    TayyorChegirma.objects.create(salon=m.salon, nomi=NOMI, foiz=FOIZ)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[l['togri'].id])
    return {'zakaz': z.id, 'raqam': z.raqam}


def topshiriq(h):
    return (f"{MIJOZ_FIO} — doimiy mijozingiz, bu uning ikkinchi zakazi (#{h['raqam']}). Salonda doimiy mijozlarga {FOIZ}% "
            f"chegirma bor. Shu zakazga «{NOMI}» chegirmasini qo'llang.")


def tekshir(m, javob=None):
    z = Zakaz.objects.filter(salon=m.salon, id=m.holat['zakaz']).first()
    if not z or z.holat == Zakaz.Holat.BEKOR:
        return [mezon(False, '', "Zakaz bekor qilingan. «Qayta boshlash» ni bosing.")]
    kutmoqda = ChegirmaSorovi.objects.filter(salon=m.salon, zakaz=z, holat=ChegirmaSorovi.Holat.KUTILMOQDA).exists()
    xato = ("Chegirma tayyor ro'yxatdan emas, so'rov qilib yuborilgan — endi rahbar qarorini kutadi. «Qayta boshlash» ni bosing."
            if kutmoqda else f"«{NOMI}» chegirmasi hali qo'llanmagan.")
    return [mezon(z.chegirma == CHEGIRMA and z.jami == IJARA - CHEGIRMA,
                  f"Chegirma qo'llandi: {som(IJARA)} → {som(IJARA - CHEGIRMA)}.", xato)] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Zakazlar» ni oching va mijozning zakazini bosing.",
            "Kartada «Boshqa amallar» ni oching, ichidan «Chegirma» ni tanlang.",
            f"«{NOMI}: −{som(CHEGIRMA)}» tugmasini bosing va so'rovni tasdiqlang.",
            "Keyin ikkita savolga javob bering: ro'yxatda yo'q chegirma qanday so'raladi."]


def yol(h):
    return [nav('Zakazlar'), zakazni_och(MIJOZ_FIO), BOSHQA_AMALLAR, amal_bolimi('Chegirma'),
            {'matn': f"Tepada — rahbar oldindan ruxsat bergan tayyor chegirmalar. «{NOMI}: −{som(CHEGIRMA)}» ni bosing.",
             'amal': 'bos', 'nishon': {'css': 'details.boshqa-amallar details.amal[open] button', 'boshi': NOMI},
             'tayyor': TASDIQ_OYNASI},
            tasdiq("Ha, qo'llash", f"Tizim yangi narxni ko'rsatyapti: {som(IJARA)} → {som(IJARA - CHEGIRMA)}. Rahbar tasdig'i kerak emas. "
                                   "«Ha, qo'llash» ni bosing.")]


def bilim(h):
    return [
        "Ro'yxatda yo'q chegirma shu bo'limning pastidan so'raladi: «Boshqa chegirma» ga foiz yoki summa, sabab va "
        "«Rahbardan so'rash». So'rov rahbarga ilovada va Telegramda boradi.",
        "Rahbar qaror qilguncha avans olinmaydi. Javob sizga qo'ng'iroqchada va Telegramda keladi; kutishni istamasangiz, "
        "so'rovni qaytarib olasiz.",
    ]


DARS = Dars(
    kod='S7', nomi="Chegirma so'rash", yonalish='sotuvchi', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi → Boshqa amallar',
    vaziyat="Mijoz chegirma so'radi. Narxni o'zingiz o'zgartira olmaysiz — bu to'g'ri: aks holda har kim har xil narx aytardi. "
            "Lekin ikki yo'l bor: rahbar oldindan ruxsat bergan tayyor chegirma va rahbardan so'raladigan chegirma.",
    natija="Tayyor chegirmani o'zingiz qo'llaysiz, ro'yxatda yo'g'ini esa rahbardan to'g'ri so'raysiz.",
    xulosa=f"Tayyor chegirma bir bosishda qo'llandi — rahbar uni oldindan ruxsat qilib qo'ygan. Ro'yxatda yo'q chegirma esa "
           "shu bo'limning pastidan so'raladi: foiz yoki summa, sabab va «Rahbardan so'rash». Ikkalasi ham faqat avans olinguncha "
           "mumkin — shuning uchun chegirmani avval hal qiling, keyin pul oling.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR,
    ishora="Chegirma zakaz kartasidagi «Boshqa amallar» ichida. Avval tayyor chegirmalar ro'yxatiga qarang.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
