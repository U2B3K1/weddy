"""S9 — Libosni qaytarib olish. Libos tekshiriladi, garov mijozga qaytariladi (P4 shu darsning ichida)."""
from apps.cash.models import Tolov
from apps.cash.services import pul_oladimi, tolov_qabul
from apps.orders.models import Zakaz, Zalog
from apps.orders.rental import libos_berish

from .asos import GAROV, MIJOZ_FIO, Dars, mezon, nav, som
from .s8 import ASOSIY_AMAL, QOLDIQ, ZAKAZ_QATORI, bronli_zakaz


def urug(m):
    """Libos mijozda: qoldiq to'langan, pul garov olingan, zakaz «Berildi»."""
    z = bronli_zakaz(m)
    tolov_qabul(salon=m.salon, xodim=m.xodim, tur=Tolov.Tur.QOLDIQ, summa=QOLDIQ, zakaz=z)
    libos_berish(salon=m.salon, xodim=m.xodim, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': GAROV}])
    return {'zakaz': z.id, 'raqam': z.raqam}


def topshiriq(h):
    return (f"{MIJOZ_FIO} libosni qaytarib keldi (#{h['raqam']}-zakaz). Libosni ko'zdan kechirdingiz — butun, dog' yo'q. "
            f"Qaytarishni rasmiylashtiring va {som(GAROV)} garovni mijozga qaytaring.")


def tekshir(m, javob=None):
    z = Zakaz.objects.filter(salon=m.salon, id=m.holat['zakaz']).first()
    if not z:
        return [mezon(False, '', "Zakaz topilmadi. «Qayta boshlash» ni bosing.")]
    if z.holat == Zakaz.Holat.BERILDI:
        return [mezon(False, '', "Qaytarish hali rasmiylashtirilmagan — libos tizimda hamon mijozda turibdi.")]
    akt = getattr(z, 'qaytarish_akti', None)
    garov = Zalog.objects.filter(salon=m.salon, zakaz=z, turi=Zalog.Turi.PUL).first()
    qaytarildi = Tolov.objects.filter(salon=m.salon, zakaz=z, tur=Tolov.Tur.ZALOG_QAYTARISH).count()
    return [
        mezon(akt and akt.tekshiruv == 'butun' and akt.jarima == 0, "Libos «butun» deb qabul qilindi, jarima yo'q.",
              "Libos butun edi, lekin tizimga nuqson yoki jarima yozilgan — mijozdan ortiqcha pul ushlanadi."),
        mezon(garov and garov.holat == Zalog.Holat.QAYTARILDI and qaytarildi == 1,
              f"Garov {som(GAROV)} mijozga bir marta qaytarildi.", "Garov to'liq qaytarilmagan."),
        mezon(z.holat in (Zakaz.Holat.QAYTARILDI, Zakaz.Holat.YOPILDI), "Zakaz yakunlandi.", "Zakaz yakunlanmagan."),
    ]


def qadamlar(h):
    return ["Menyuda «Zakazlar» ni oching va ro'yxatdan mijozning zakazini bosing.",
            "«Qaytarish» bo'limida «Holat tekshiruvi» — «Butun» turibdi, «Jarima» bo'sh qoladi.",
            f"Yuqorida «Pul garov {som(GAROV)} — mijozga qaytariladi» deb yozilganini tekshiring.",
            "«Qaytarishni rasmiylashtirish» ni bosing va garovni mijozga bering."]


def yol(h):
    return [nav('Zakazlar'),
            {'matn': f"Ro'yxatdan {MIJOZ_FIO}ning zakazini oching.", 'amal': 'bos', 'nishon': ZAKAZ_QATORI,
             'tayyor': ASOSIY_AMAL},
            {'matn': f"Libos butun — «Holat tekshiruvi» «Butun» da qoladi, jarima yozilmaydi. Tizim {som(GAROV)} garov mijozga "
                     "qaytishini ko'rsatyapti. «Qaytarishni rasmiylashtirish» ni bosing.", 'amal': 'bos',
             'nishon': ASOSIY_AMAL, 'ichki': {'css': 'button', 'matn': 'Qaytarishni rasmiylashtirish'}}]


DARS = Dars(
    kod='S9', nomi='Libosni qaytarib olish', yonalish='sotuvchi', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi',
    vaziyat="To'y o'tdi, mijoz libosni qaytarib keldi. Avval libosni ko'zdan kechiramiz, keyin garovini qaytaramiz. "
            "Tizimga yozilmaguncha libos hamon «mijozda» hisoblanadi.",
    natija="Qaytgan libosni qabul qilib, garovni to'g'ri qaytara olasiz.",
    xulosa="Qaytarish rasmiylashtirildi: garov kassadan chiqib mijozga qaytdi, libos tozalashga o'tdi va bir necha kundan "
           "keyin yana ijaraga chiqadi. Agar libosda dog' yoki yirtiq bo'lsa, «Holat tekshiruvi» da shuni tanlab, jarima "
           "yoziladi — u avval garovdan ushlanadi.",
    tekshirilgan='2026-11-13 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=pul_oladimi,
    ishora="Qaytarish ham zakaz kartasida. Libos butun bo'lsa, hech narsa o'zgartirmasdan rasmiylashtiriladi — garov "
           "to'liq qaytadi.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
