"""S8 — Libosni topshirish. Qoldiq to'liq olinadi, garov alohida qabul qilinadi, shundan keyingina libos beriladi.
Garovni qabul qilish (P3) shu darsning ichida: haqiqiy ishda bu bitta harakat."""
from datetime import timedelta

from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import pul_oladimi, smena_ochish, tolangan_summa, tolov_qabul
from apps.orders.models import Zakaz, Zalog
from apps.orders.services import zakaz_yaratish

from .asos import AVANS, GAROV, IJARA, MIJOZ_FIO, MIJOZ_TELEFON, Dars, katalog, mezon, nav, som

QOLDIQ = IJARA - AVANS
ZAKAZ_QATORI = {'css': 'tbody tr, button.zt-karta', 'ichida': MIJOZ_FIO}
ASOSIY_AMAL = {'css': '#asosiy-amal'}  # zakaz kartasidagi navbatdagi amal (to'lov, berish, qaytarish)


def bronli_zakaz(m):
    """Bugun olib ketiladigan, avansi olingan zakaz va ochiq smena — topshirish va qaytarish darslarining boshlanishi."""
    l = katalog(m)
    bugun = timezone.localdate()
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=bugun,
                       qaytarish=bugun + timedelta(days=2), libos_idlari=[l['togri'].id])
    smena_ochish(salon=m.salon, xodim=m.xodim, boshlangich_qoldiq=0)
    tolov_qabul(salon=m.salon, xodim=m.xodim, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z)
    return z


def urug(m):
    z = bronli_zakaz(m)
    return {'zakaz': z.id, 'raqam': z.raqam}


def topshiriq(h):
    return (f"{MIJOZ_FIO} libosni olib ketgani keldi (#{h['raqam']}-zakaz). Avans {som(AVANS)} olingan. Qolgan {som(QOLDIQ)} ni "
            f"naqd qabul qiling, {som(GAROV)} pul garov oling va libosni bering.")


def tekshir(m, javob=None):
    z = Zakaz.objects.filter(salon=m.salon, id=m.holat['zakaz']).first()
    if not z or z.holat == Zakaz.Holat.BEKOR:
        return [mezon(False, '', "Zakaz bekor qilingan. «Qayta boshlash» ni bosing.")]
    tolangan = tolangan_summa(z)
    garovlar = list(Zalog.objects.filter(salon=m.salon, zakaz=z))
    pul = [g for g in garovlar if g.turi == Zalog.Turi.PUL]
    return [
        mezon(tolangan == z.jami, "Ijara haqi to'liq olingan.",
              f"Ijara haqidan {som(z.jami - tolangan)} olinmagan — qoldiq to'lanmaguncha libos berilmaydi."),
        mezon(len(pul) == 1 and pul[0].summa == GAROV, f"Garov alohida olingan: {som(GAROV)}.",
              "Garov olinmagan." if not garovlar else f"Garov {som(GAROV)} pul bo'lishi kerak edi."),
        mezon(z.holat == Zakaz.Holat.BERILDI, "Libos berildi — zakaz «Berildi» holatida.", "Libos hali berilmagan."),
    ]


def qadamlar(h):
    return ["Menyuda «Zakazlar» ni oching va ro'yxatdan mijozning zakazini bosing.",
            f"«Qoldiq to'lov» da summa {som(QOLDIQ)} turibdi, usul — naqd. «Qabul qilish» ni bosing.",
            f"Endi «Libosni berish (garov)» chiqadi: garov turi — pul, summasi {som(GAROV)}.",
            "«Garovni qabul qilib berish» ni bosing."]


def yol(h):
    return [nav('Zakazlar'),
            {'matn': f"Ro'yxatdan {MIJOZ_FIO}ning zakazini oching.", 'amal': 'bos', 'nishon': ZAKAZ_QATORI,
             'tayyor': ASOSIY_AMAL},
            {'matn': f"Avval qoldiq: «Qoldiq to'lov» da {som(QOLDIQ)} va «Naqd» turibdi. «Qabul qilish» ni bosing.", 'amal': 'bos',
             'nishon': ASOSIY_AMAL, 'ichki': {'css': 'button', 'matn': 'Qabul qilish'}},
            {'matn': f"Endi garov: turi — pul, summasi {som(GAROV)}. Bu ijara haqi emas — libos qaytganda mijozga qaytariladi. "
                     "«Garovni qabul qilib berish» ni bosing.", 'amal': 'bos',
             'nishon': ASOSIY_AMAL, 'ichki': {'css': 'button', 'matn': 'Garovni qabul qilib berish'}}]


DARS = Dars(
    kod='S8', nomi='Libosni topshirish', yonalish='sotuvchi', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi',
    vaziyat="To'y kuni keldi — mijoz libosni olib ketadi. Libos qo'ldan chiqishidan oldin ikki narsa bo'lishi shart: "
            "ijara haqi to'liq to'langan va garov olingan.",
    natija="Qoldiqni olib, garovni alohida yozib, libosni to'g'ri topshira olasiz.",
    xulosa="Libos berildi. E'tibor bering: ikki xil pul oldingiz. Qoldiq — ijara haqi, salonning daromadi. Garov — mijozning "
           "puli: u seyfda turadi va libos butun qaytganda qaytariladi. Tizim ularni alohida yozadi; aralashtirsangiz, "
           "kun oxirida kassa to'g'ri kelmaydi.",
    tekshirilgan='2026-11-13 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=pul_oladimi,
    ishora="Topshirish zakaz kartasida bajariladi. Tartib qat'iy: avval qoldiq to'lov, keyin garov — shundan keyin "
           "«berish» tugmasi chiqadi.",
    qadamlar=qadamlar, yol=yol, xp=70,
)
