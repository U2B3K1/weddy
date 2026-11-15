"""P2 — Avansni qabul qilish. Faqat pul bilan ishlaydigan xodimga (kassa rejimiga qarab) beriladi."""
from apps.cash.models import Tolov
from apps.cash.services import pul_oladimi, smena_ochish, tolangan_summa
from apps.orders.models import Zakaz
from apps.orders.services import zakaz_yaratish

from .asos import AVANS, MIJOZ_FIO, MIJOZ_TELEFON, Dars, mezon, nav, som, tab, toy_katalogi


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[l['togri'].id])
    smena_ochish(salon=m.salon, xodim=m.xodim, boshlangich_qoldiq=0)  # dars to'lov haqida — smena ochiq turadi
    return {'zakaz': z.id, 'raqam': z.raqam}


def topshiriq(h):
    return (f"{MIJOZ_FIO} #{h['raqam']}-zakaz uchun {som(AVANS)} avansni naqd berdi. Shu zakazga avansni qabul qiling. "
            f"Smena ochiq.")


def tekshir(m, javob=None):
    z = Zakaz.objects.filter(salon=m.salon, id=m.holat['zakaz']).first()
    if not z or z.holat == Zakaz.Holat.BEKOR:
        return [mezon(False, '', "Zakaz bekor qilingan. «Qayta boshlash» ni bosing.")]
    tolovlar = list(Tolov.objects.filter(Tolov.HAQIQIY, salon=m.salon, zakaz=z))
    if not tolovlar:
        # ro'yxatda boshqa mijozning zakazi ham turadi — pul unga yozilib ketishi mumkin
        boshqa = Tolov.objects.filter(Tolov.HAQIQIY, salon=m.salon, zakaz__isnull=False).exclude(zakaz=z).select_related('zakaz').first()
        return [mezon(False, '', f"To'lov boshqa zakazga (#{boshqa.zakaz.raqam}) yozilgan. {MIJOZ_FIO}ning zakazi — #{z.raqam}. "
                                 "«Qayta boshlash» ni bosib, qaytadan urinib ko'ring." if boshqa
                      else "Bu zakazga hali to'lov yozilmagan.")]
    jami = tolangan_summa(z)
    return [
        mezon(jami == AVANS, "Summa to'g'ri.", f"Zakazga {som(jami)} yozilgan, mijoz esa {som(AVANS)} bergan."),
        mezon(all(t.usul == Tolov.Usul.NAQD for t in tolovlar), "To'lov usuli to'g'ri: naqd.",
              "To'lov usuli noto'g'ri: mijoz naqd bergan."),
        mezon(z.holat == Zakaz.Holat.BRON, "Bron tasdiqlandi: libos endi shu mijozga band.",
              "Zakaz hali vaqtinchalik bronda."),
    ]


def qadamlar(h):
    return ["Menyuda «Kassa» ni oching va tepadan «To'lov qabul» bo'limini tanlang.",
            f"«To'lov kutayotgan zakazlar» ro'yxatidan #{h['raqam']}-zakazni ({MIJOZ_FIO}) tanlang.",
            f"Summa to'liq narx bilan to'lib turadi. «⌫» bilan o'chirib, klaviaturadan {som(AVANS)[:-5]} tering.",
            f"«To'lov usuli» da «Naqd» ni tanlang va «{som(AVANS)} qabul qilish» tugmasini bosing."]


def yol(h):
    summa = som(AVANS)
    return [nav('Kassa'), tab("To'lov qabul"),
            {'matn': f"«To'lov kutayotgan zakazlar» dan {MIJOZ_FIO}ning zakazini (#{h['raqam']}) tanlang.", 'amal': 'bos',
             'nishon': {'css': '.pos-zakazlar'}, 'ichki': {'css': 'button.pos-zakaz'}},
            # summa to'liq narx bilan to'lib turadi — o'quvchi uni o'zi tuzatadi
            {'matn': f"Summa to'liq narx bilan to'lib turibdi. «⌫» bilan o'chirib, {summa[:-5]} tering.", 'amal': 'bos',
             'nishon': {'css': '.klaviatura'}, 'tayyor': {'css': '.pos-chek button', 'boshi': f'{summa} qabul qilish'}},
            {'matn': "To'lov usuli: «Naqd» ni tanlang.", 'amal': 'bos', 'nishon': {'css': '.pos-usullar button', 'matn': 'Naqd'}},
            {'matn': f"«{summa} qabul qilish» tugmasini bosing.", 'amal': 'bos',
             'nishon': {'css': '.pos-chek button', 'ichida': 'qabul qilish'}}]


DARS = Dars(
    kod='P2', nomi='Avansni qabul qilish', yonalish='pul', personaj='madina',
    sahifa="Kassa → To'lov qabul",
    vaziyat="Mijoz zakazni tasdiqlab, avans beryapti. Avans yozilmaguncha bron vaqtinchalik — 24 soatdan keyin o'zi bekor bo'ladi. "
            "Pulni olgan zahoti tizimga yozamiz.",
    natija="Avansni to'g'ri zakazga, to'g'ri summa va to'g'ri usul bilan yoza olasiz.",
    xulosa="Avans yozildi va bron tasdiqlandi: libos endi shu mijozga band. Qolgan summa libos topshirilayotganda olinadi. "
           "Garov — alohida pul: u avansga qo'shilmaydi va libos qaytganda qaytariladi.",
    tekshirilgan='2026-11-12 · 1f405b7 dan keyingi ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=pul_oladimi,
    ishora="Avans — ijara haqining bir qismi. U Kassadagi «To'lov qabul» bo'limida, aynan shu zakaz tanlanib yoziladi.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
