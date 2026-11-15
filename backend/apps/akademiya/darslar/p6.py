"""P6 — Smenani yopish. Kun oxiri: naqd sanaladi, tizim bilan solishtiriladi, pul seyfda qoladi."""
from apps.cash.models import Smena, Tolov
from apps.cash.services import pul_oladimi, smena_ochish, tolov_qabul
from apps.orders.services import zakaz_yaratish

from .asos import AVANS, MIJOZ_FIO, MIJOZ_TELEFON, Dars, mezon, nav, som, toy_katalogi

BOSHLANGICH = 200_000
KASSADA = BOSHLANGICH + AVANS


def urug(m):
    """Kun davomida bo'lgan ishlar: smena 200 000 bilan ochilgan, bitta avans (100 000, naqd) olingan."""
    l, dan, gacha = toy_katalogi(m)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[l['togri'].id])
    s = smena_ochish(salon=m.salon, xodim=m.xodim, boshlangich_qoldiq=BOSHLANGICH)
    tolov_qabul(salon=m.salon, xodim=m.xodim, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z)
    return {'smena': s.id}


def topshiriq(h):
    return (f"Ish kuni tugadi. Ertalab seyfda {som(BOSHLANGICH)} bor edi, kun davomida {som(AVANS)} avans oldingiz. "
            f"Kassadagi naqdni sanadingiz: {som(KASSADA)}. Smenani yoping — pul seyfda qoladi.")


def tekshir(m, javob=None):
    s = Smena.objects.filter(salon=m.salon, id=m.holat['smena']).first()
    if not s or s.yopilgan is None:
        return [mezon(False, '', "Smena hali yopilmagan.")]
    return [
        mezon(s.fakt_qoldiq == KASSADA, "Sanalgan naqd to'g'ri kiritilgan.",
              f"Sanalgan naqd {som(s.fakt_qoldiq or 0)} deb kiritilgan, kassada esa {som(KASSADA)} bor edi."),
        mezon(s.farq == 0, "Farq yo'q: tizimdagi va sanalgan pul bir xil.",
              f"Smena {som(s.farq or 0)} farq bilan yopildi — buni rahbar ko'radi va sababini so'raydi."),
    ]


def qadamlar(h):
    return ["Menyuda «Kassa» ni oching.",
            "Smena qatoridagi «Smenani yopish» ni bosing.",
            f"Klaviaturadan sanalgan naqdni tering: {som(KASSADA)[:-5]}. «Farq yo'q» chiqishi kerak.",
            "«Pul qayerda qoladi?» — «Seyfda — ertangi smenaga» tanlangan holda qoladi.",
            "«Smenani yopish» ni bosing va so'rovni tasdiqlang."]


def yol(h):
    summa = som(KASSADA)[:-5]
    return [nav('Kassa'),
            {'matn': "Smena qatoridagi «Smenani yopish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': 'main button', 'matn': 'Smenani yopish'}, 'tayyor': {'css': '[role=dialog] .smena-yopish'},
             # telefonda Kassa bosh ekranida smena tugmalari yo'q — smena «Smena hisoboti» dagi «Kun yakuni» da yopiladi
             'muqobil': {'css': '.kassa-uy button.tb-qator', 'matn': 'Smena hisoboti'},
             'muqobil_matn': "Telefonda smena «Smena hisoboti» sahifasida yopiladi. Avval yoritilgan «Smena hisoboti» ni bosing."},
            {'matn': f"Sanalgan naqdni kiriting: klaviaturadan {summa} tering. Tizim farqni o'zi ko'rsatadi.", 'amal': 'bos',
             'nishon': {'css': '[role=dialog] .klaviatura'}, 'tayyor': {'css': '[role=dialog] .sy-summa b', 'matn': summa}},
            {'matn': "«Farq yo'q» chiqdi. Pul seyfda qoladi. «Smenani yopish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': '[role=dialog] button.pos-tugma'}, 'tayyor': {'css': '[role=alertdialog]'}},
            {'matn': "Yopilgan smenani o'zgartirib bo'lmaydi. Tasdiqlang: «Smenani yopish».", 'amal': 'bos',
             'nishon': {'css': '[role=alertdialog] button', 'matn': 'Smenani yopish'}}]


DARS = Dars(
    kod='P6', nomi='Smenani yopish', yonalish='pul', personaj='madina',
    sahifa='Kassa → Smenani yopish',
    vaziyat="Salon yopilyapti. Ketishdan oldin kassadagi naqdni sanaymiz va tizimdagi summa bilan solishtiramiz. "
            "Bir so'm ham farq qilmasligi kerak.",
    natija="Kun oxirida naqdni sanab, smenani farqsiz yopa olasiz.",
    xulosa="Smena farqsiz yopildi: sanalgan pul tizimdagiga teng. Agar farq chiqsa, tizim sababini yozishni so'raydi va "
           "rahbar buni ko'radi — shuning uchun har to'lov o'sha zahoti va to'g'ri usul bilan yoziladi. "
           "Ertaga smenani ochgan xodim seyfdagi shu pulni sanab qabul qiladi.",
    tekshirilgan='2026-11-13 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=pul_oladimi,
    ishora="Smena «Kassa» bo'limida yopiladi. Tizim kassada qancha bo'lishi kerakligini biladi — siz faqat sanalganini kiritasiz.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
