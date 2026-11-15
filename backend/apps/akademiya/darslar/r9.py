"""R9 — Smena farqini tekshiramiz (rahbar). Vaziyat: sotuvchi terminaldan o'tgan 50 000 so'mlik avansni «naqd» deb yozgan —
tizim bo'yicha kassada naqd ko'p, terminalda esa kam. Smena ochiq paytda rahbar to'lov usulini zakaz kartasida tuzatadi
(Zakazlar.jsx TolovTuzatish → cash.services.tolov_tuzatish); yopilgan smena — Kassa → Smenalar tarixi → «Tuzatish»."""
from datetime import timedelta

from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import kassa_hisobot, smena_ochish, tolov_qabul
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import sozlama

from .asos import (AVANS, BAND_FIO, BAND_TELEFON, MIJOZ_FIO, MIJOZ_TELEFON, Dars, faqat_rahbar, katalog, mezon, nav,
                   savollarni_tekshir, som, tab, toy_sanalari, zakazni_och)

XATO_SUMMA = 50_000
TIZIMDA, QOLDA = AVANS + XATO_SUMMA, AVANS
TUZATISH = 'details.tolov-tuzatish'

SAVOLLAR = [
    {'matn': "To'lov usuli tuzatildi. Endi tizim bo'yicha kassada qancha naqd bo'lishi kerak?",
     'variantlar': [
         ('eski', som(TIZIMDA), False, f"Bu — tuzatishdan oldingi raqam. {som(XATO_SUMMA)} endi terminalga o'tdi: naqd {som(QOLDA)}."),
         ('togri', som(QOLDA), True, f"To'g'ri: {som(TIZIMDA)} − {som(XATO_SUMMA)} = {som(QOLDA)} — sotuvchi sanagan pul bilan bir xil. Farq yo'qoldi."),
         ('kam', som(XATO_SUMMA), False, f"{som(XATO_SUMMA)} — terminalga o'tgan summa. Naqd esa {som(QOLDA)} qoldi."),
     ]},
    {'matn': "Xuddi shunday xato ertasi kuni — smena yopilib bo'lgach — bilinsa-chi?",
     'variantlar': [
         ('iloj', "Endi hech narsa qilib bo'lmaydi", False,
          "Qilsa bo'ladi: Kassa → «Smenalar tarixi» da smenani ochib, «Tuzatish» orqali sanalgan summa va izohni yozasiz."),
         ('tarix', "Kassa → «Smenalar tarixi» → smena → «Tuzatish»: qayta sanalgan summa va izoh", True,
          "To'g'ri: yopilgan smenada to'lovning o'zi emas, smena natijasi tuzatiladi — sababi izohda, o'zgarish jurnalda qoladi."),
         ('ochir', "To'lovni o'chirib, qaytadan yozdiraman", False,
          "To'lov o'chirilmaydi — tizimda pul izsiz yo'qolmaydi. Yopilgan smena «Smenalar tarixi» da tuzatiladi."),
     ]},
]


def urug(m):
    """Sotuvchi smena ochgan va ikki avans olgan: biri haqiqatan naqd, ikkinchisi terminaldan o'tgan, lekin «naqd» deb yozilgan."""
    s = sozlama(m.salon)
    if s.kassa_rejimi != 'sotuvchi':  # darsda pulni sotuvchining o'zi oladi
        s.kassa_rejimi = 'sotuvchi'
        s.save(update_fields=['kassa_rejimi'])
    l = katalog(m)
    sotuvchi = m.hamkasb
    bugun = timezone.localdate()
    dan, gacha = toy_sanalari()
    smena_ochish(salon=m.salon, xodim=sotuvchi, boshlangich_qoldiq=0)
    z1 = zakaz_yaratish(salon=m.salon, xodim=sotuvchi, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=bugun + timedelta(days=1),
                        qaytarish=bugun + timedelta(days=2), libos_idlari=[l['togri'].id])
    tolov_qabul(salon=m.salon, xodim=sotuvchi, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z1)
    z2 = zakaz_yaratish(salon=m.salon, xodim=sotuvchi, telefon=BAND_TELEFON, fio=BAND_FIO, olib_ketish=dan, qaytarish=gacha,
                        libos_idlari=[l['band'].id])
    t = tolov_qabul(salon=m.salon, xodim=sotuvchi, tur=Tolov.Tur.AVANS, summa=XATO_SUMMA, zakaz=z2)
    return {'tolov': t.id, 'raqam': z2.raqam, 'sotuvchi': sotuvchi.ism}


def topshiriq(h):
    return (f"{h['sotuvchi']} qo'ng'iroq qildi: «Kassada {som(QOLDA)} naqd bor, tizim esa {som(TIZIMDA)} deyapti. Terminal chekida "
            f"{som(XATO_SUMMA)}lik to'lov turibdi — {BAND_FIO}, #{h['raqam']}-zakaz». Sababini toping va smena yopilmasidan tuzating.")


def tekshir(m, javob=None):
    t = Tolov.objects.filter(salon=m.salon, id=m.holat['tolov']).select_related('smena').first()
    if not t:
        return [mezon(False, '', "To'lov topilmadi. «Qayta boshlash» ni bosing.")]
    naqd = kassa_hisobot(t.smena)['hisobdagi_qoldiq']
    return [
        mezon(t.usul == Tolov.Usul.KARTA and t.summa == XATO_SUMMA, f"{som(XATO_SUMMA)}lik to'lov endi «Terminal» — summasi o'zgarmadi.",
              "To'lov usuli hali «Naqd» turibdi." if t.usul == Tolov.Usul.NAQD
              else f"To'lov noto'g'ri tuzatilgan: usul «Terminal», summa {som(XATO_SUMMA)} bo'lishi kerak."),
        mezon(naqd == QOLDA, f"Tizimdagi naqd {som(QOLDA)} — kassadagi pul bilan teng.", f"Tizim bo'yicha kassada hamon {som(naqd)}."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["«Kassa» → «Smena hisoboti»: tizim bo'yicha naqd va terminal summalarini ko'ring.",
            f"«Pul harakatlari» da {som(XATO_SUMMA)}lik naqd to'lovni toping — u aslida terminaldan o'tgan.",
            f"«Zakazlar» da {BAND_FIO}ning zakazini oching. «To'lovlar» dagi avans yonida «Tuzatish» ni bosing.",
            "To'lov usulini «Terminal» qiling, sababini yozing va «Tuzatishni saqlash» ni bosing."]


def yol(h):
    return [nav('Kassa'), tab('Smena hisoboti'),
            {'matn': f"Tizim bo'yicha: kassada naqd {som(TIZIMDA)}, terminal — 0. {h['sotuvchi']} esa {som(QOLDA)} naqd sanadi va terminal "
                     f"chekida {som(XATO_SUMMA)} bor. Demak {som(XATO_SUMMA)}lik to'lov noto'g'ri usul bilan yozilgan.", 'amal': 'kor',
             'nishon': {'css': '.smena-kpi'}},
            {'matn': f"«Pul harakatlari» da har bir to'lov usuli bilan turibdi. {som(XATO_SUMMA)} — «Naqd» deb yozilgan avans: aynan shu "
                     "terminaldan o'tgan. Uni zakaz kartasida tuzatamiz.", 'amal': 'kor',
             'nishon': {'css': 'section[aria-label="Pul harakatlari"]'}},
            nav('Zakazlar'), zakazni_och(BAND_FIO),
            {'matn': f"«To'lovlar» ro'yxatida avans {som(XATO_SUMMA)} — «Naqd». Yonidagi «Tuzatish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': f'{TUZATISH} > summary'}, 'tayyor': {'css': f'{TUZATISH}[open]'}},
            {'matn': "To'lov usulini «Terminal» ga o'zgartiring.", 'amal': 'yoz',
             'nishon': {'css': f'{TUZATISH}[open] select'}, 'kutilgan': 'matn:karta'},
            {'matn': "Sababini yozing — u jurnalda qoladi va sotuvchiga ham boradi. Masalan: terminaldan o'tgan edi.", 'amal': 'yoz',
             'nishon': {'css': f'{TUZATISH}[open] input', 'placeholder': 'masalan'}, 'kutilgan': 'uzunlik:5'},
            {'matn': "Summa o'zgarmaydi. «Tuzatishni saqlash» ni bosing.", 'amal': 'bos',
             'nishon': {'css': f'{TUZATISH}[open] button', 'matn': 'Tuzatishni saqlash'},
             'tayyor': {'css': '.karta-ong p.malumot', 'ichida': "To'lov tuzatildi"}}]


def bilim(h):
    return [
        "To'lov usuli tuzatilgach, tizimdagi naqd shu summaga kamayadi, terminal esa shuncha ko'payadi — jami pul o'zgarmaydi.",
        "Xato smena yopilgandan keyin bilinsa, to'lovning o'zi emas, smena natijasi tuzatiladi: Kassa → «Smenalar tarixi» → smena → "
        "«Tuzatish» — qayta sanalgan summa va izoh bilan.",
    ]


DARS = Dars(
    kod='R9', nomi='Smena farqini tekshiramiz', yonalish='rahbar', personaj='nodira',
    sahifa='Kassa → Smena hisoboti · zakaz kartasi',
    vaziyat="Kassadagi pul tizimdagi raqam bilan to'g'ri kelmayapti. Bu har doim ham o'g'irlik emas — ko'pincha oddiy xato: "
            "to'lov boshqa usul bilan yozilgan yoki summa xato terilgan. Sababini topish uchun uchta raqam yetadi.",
    natija="Kassa farqining sababini topasiz va noto'g'ri yozilgan to'lovni tuzatasiz.",
    xulosa="Farq yo'qoldi, hech kim «kamomad» bilan qolmadi. Tartib doim bir xil: naqd, terminal va sotuvchi sanagan pulni solishtirasiz, "
           "«Pul harakatlari» dan shubhali to'lovni topasiz, zakaz kartasida tuzatasiz — sabab bilan. Tuzatish jurnalga yoziladi va "
           "sotuvchiga xabar boradi. Farq baribir qolsa — smena shu farq bilan yopiladi va u sotuvchining hisobida ko'rinadi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Naqd ko'p, terminal kam — demak qaysidir to'lov noto'g'ri usul bilan yozilgan. Uni «Pul harakatlari» dan toping.",
    qadamlar=qadamlar, yol=yol, xp=80,
)
