"""P1 — Smenani ochish. Kun shu bilan boshlanadi: smena ochilmaguncha tizim pul qabul qilmaydi."""
from apps.cash.models import Smena
from apps.cash.services import pul_oladimi

from .asos import Dars, mezon, nav, som, toy_katalogi

SEYFDA = 200_000


def urug(m):
    toy_katalogi(m)  # salon bo'sh ko'rinmasin: liboslar va bitta band zakaz
    return {}


def topshiriq(h):
    return (f"Ish kuni boshlandi. Seyfdagi naqd pulni sanadingiz: {som(SEYFDA)}. Shu summa bilan smenani oching.")


def tekshir(m, javob=None):
    s = Smena.objects.filter(salon=m.salon, yopilgan__isnull=True).first()
    if not s:
        return [mezon(False, '', "Smena hali ochilmagan.")]
    return [
        mezon(s.ochgan_id == m.xodim.id, "Smenani o'zingiz ochdingiz.", "Smenani boshqa xodim ochgan."),
        mezon(s.boshlangich_qoldiq == SEYFDA, "Boshlang'ich qoldiq to'g'ri.",
              f"Boshlang'ich qoldiq {som(s.boshlangich_qoldiq)} deb yozilgan, seyfda esa {som(SEYFDA)} bor edi. "
              "Kun oxirida shu farq sizning hisobingizda chiqadi."),
    ]


def qadamlar(h):
    return ["Menyuda «Kassa» ni oching.",
            "«Smena yopiq» yozuvi yonidagi «Smenani ochish» ni bosing.",
            f"Klaviaturadan {som(SEYFDA)[:-5]} tering — bu seyfda sanalgan naqd pul.",
            "Oynadagi «Smenani ochish» tugmasini bosing."]


def yol(h):
    summa = som(SEYFDA)[:-5]
    return [nav('Kassa'),
            {'matn': "Smena yopiq. «Smenani ochish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': 'main button', 'matn': 'Smenani ochish'}, 'tayyor': {'css': '[role=dialog] .klaviatura'}},
            {'matn': f"Seyfdagi naqdni kiriting: klaviaturadan {summa} tering.", 'amal': 'bos',
             'nishon': {'css': '[role=dialog] .klaviatura'}, 'tayyor': {'css': '[role=dialog] .pos-summa b', 'matn': summa}},
            {'matn': "Summa to'g'ri. Oynadagi «Smenani ochish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': '[role=dialog] button.pos-tugma'}}]


DARS = Dars(
    kod='P1', nomi='Smenani ochish', yonalish='pul', personaj='madina',
    sahifa='Kassa → Smenani ochish',
    vaziyat="Ertalab salonga birinchi bo'lib keldingiz. Mijoz pul bermoqchi, lekin smena ochilmagan — tizim to'lovni qabul "
            "qilmaydi. Avval seyfdagi pulni sanab, smenani ochamiz.",
    natija="Ish kunini to'g'ri boshlay olasiz: seyfni sanab, smenani ochasiz.",
    xulosa="Smena ochildi — endi to'lov qabul qilsa bo'ladi. Boshlang'ich qoldiq — bu sizdan oldin seyfda turgan pul: uni "
           "noto'g'ri kiritsangiz, kun oxirida farq chiqadi va rahbar ko'radi. Kun oxirida smena xuddi shunday sanab yopiladi.",
    tekshirilgan='2026-11-13 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=pul_oladimi,
    ishora="Smena — kassaning ish kuni. U «Kassa» bo'limida ochiladi va seyfdagi naqd pulni sanashdan boshlanadi.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
