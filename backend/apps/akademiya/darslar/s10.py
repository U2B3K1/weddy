"""S10 — Kechikkan zakaz. Libos qaytarish kunidan kech keldi: tizim kechikkan kunlarni o'zi sanaydi va jarimani
(kun × kunlik summa, Sozlama → Kechikish jarimasi) qaytarish paytida o'zi hisoblaydi; jarima avval pul garovidan
ushlanadi, ortig'i — to'lov yoki mijoz qarzi (rental.libos_qaytarish, Zakazlar.jsx QaytarishForma)."""
from datetime import timedelta

from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import pul_oladimi, smena_ochish, tolov_qabul
from apps.orders.models import Zakaz
from apps.orders.rental import libos_berish
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import sozlama

from .asos import (GAROV, MIJOZ_FIO, MIJOZ_TELEFON, Dars, katalog, mezon, nav, otgan_sanaga, savollarni_tekshir, som,
                   zakazni_och)
from .s8 import ASOSIY_AMAL

KUNLIK, KUN = 50_000, 1
JARIMA = KUNLIK * KUN
QAYTADI = GAROV - JARIMA

SAVOLLAR = [
    {'matn': f"Mijoz {som(GAROV)} garov bergan edi. Qaytarish rasmiylashtirildi. Unga qancha pul qaytarasiz?",
     'variantlar': [
         ('hammasi', som(GAROV), False,
          f"Garovning hammasi qaytmaydi: {KUN} kun kechikkani uchun {som(JARIMA)} jarima undan ushlandi."),
         ('farq', som(QAYTADI), True,
          f"To'g'ri: {som(GAROV)} garov − {som(JARIMA)} jarima = {som(QAYTADI)}. Tizim buni o'zi hisoblab, ekranda ko'rsatdi."),
         ('nol', "Hech narsa", False, f"Jarima {som(JARIMA)}, garov esa {som(GAROV)} — farqi {som(QAYTADI)} mijozga qaytadi."),
     ]},
    {'matn': f"Boshqa mijoz 3 kun kechikdi: jarima {som(3 * KUNLIK)}, garovi esa {som(GAROV)}. Yetmagan {som(3 * KUNLIK - GAROV)} nima bo'ladi?",
     'variantlar': [
         ('kechir', "Kechiriladi — garovdan ortig'i olinmaydi", False,
          "Kechirilmaydi: garov yetmasa, qolganini mijoz qo'shimcha to'laydi."),
         ('qarz', "Mijoz hozir to'laydi; to'lamasa — tizim uni qarz deb yozadi", True,
          "To'g'ri: «hozir to'landi» belgilanmasa, summa mijozning qarzi bo'lib qoladi — zakaz yopilmaydi va u «Qarzdorlar» da turadi."),
         ('sotuvchi', "Sotuvchining hisobidan ushlanadi", False,
          "Sizdan ushlanmaydi: bu mijozning qarzi. Tizim uni mijoz nomiga yozadi."),
     ]},
]


def urug(m):
    s = sozlama(m.salon)
    s.kechikish_jarimasi, s.kechikish_kunlik_summa = True, KUNLIK
    s.save(update_fields=['kechikish_jarimasi', 'kechikish_kunlik_summa'])
    l = katalog(m)
    bugun = timezone.localdate()
    smena_ochish(salon=m.salon, xodim=m.xodim, boshlangich_qoldiq=0)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=bugun,
                       qaytarish=bugun, libos_idlari=[l['togri'].id])
    tolov_qabul(salon=m.salon, xodim=m.xodim, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
    libos_berish(salon=m.salon, xodim=m.xodim, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': GAROV}])
    otgan_sanaga(z, bugun - timedelta(days=KUN + 2), bugun - timedelta(days=KUN))
    return {'zakaz': z.id, 'raqam': z.raqam}


def topshiriq(h):
    return (f"{MIJOZ_FIO} libosni kecha qaytarishi kerak edi — bugun olib keldi (#{h['raqam']}-zakaz). Libos butun. "
            "Qaytarishni rasmiylashtiring: jarimani tizim o'zi hisoblaydi.")


def tekshir(m, javob=None):
    z = Zakaz.objects.filter(salon=m.salon, id=m.holat['zakaz']).first()
    if not z:
        return [mezon(False, '', "Zakaz topilmadi. «Qayta boshlash» ni bosing.")]
    akt = getattr(z, 'qaytarish_akti', None)
    if z.holat == Zakaz.Holat.BERILDI or not akt:
        return [mezon(False, '', "Qaytarish hali rasmiylashtirilmagan — libos tizimda hamon mijozda turibdi.")]
    return [
        mezon(akt.kechikish_kunlari == KUN and akt.jarima == JARIMA,
              f"Kechikish {KUN} kun — jarima {som(JARIMA)}: tizim o'zi hisobladi.",
              f"Jarima {som(akt.jarima)} deb yozilgan. Libos butun edi — faqat kechikish jarimasi {som(JARIMA)} bo'lishi kerak. "
              "«Jarima» maydoniga qo'lda hech narsa yozilmaydi."),
        mezon(akt.ushlab_qolingan == JARIMA and akt.qarz == 0, f"Jarima garovdan ushlandi, mijozga {som(QAYTADI)} qaytadi.",
              "Jarima garovdan to'g'ri ushlanmagan."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Zakazlar» ni oching: kechikkan zakaz qizil «1 kun kechikdi» belgisi bilan turibdi. Uni oching.",
            f"«Qaytarish» bo'limida tizim yozgan: «Kechikish: {KUN} kun · avtomatik jarima {som(JARIMA)}».",
            "«Holat tekshiruvi» — «Butun», «Jarima» maydoni bo'sh qoladi (u faqat libosga zarar yetganda to'ldiriladi).",
            "«Qaytarishni rasmiylashtirish» ni bosing."]


def yol(h):
    return [nav('Zakazlar'),
            {**zakazni_och(MIJOZ_FIO, f"Kechikkan zakaz ro'yxatda qizil «{KUN} kun kechikdi» belgisi bilan turibdi — bu {MIJOZ_FIO}. Uni oching."),
             'tayyor': ASOSIY_AMAL},
            {'matn': f"Tizim kechikishni o'zi sanadi: {KUN} kun · jarima {som(JARIMA)}. Libos butun — «Jarima» maydoniga hech narsa "
                     "yozmaysiz. «Qaytarishni rasmiylashtirish» ni bosing.", 'amal': 'bos',
             'nishon': ASOSIY_AMAL, 'ichki': {'css': 'button', 'matn': 'Qaytarishni rasmiylashtirish'}}]


def bilim(h):
    return [
        "Jarima garovdan ushlanadi: mijozga garov − jarima qaytariladi. Tizim summani o'zi hisoblab, ekranda ko'rsatadi.",
        "Jarima garovdan katta bo'lsa, yetmagan qismini mijoz hozir to'laydi. To'lamasa — tizim uni qarz deb yozadi va mijoz "
        "«Qarzdorlar» ro'yxatida turadi.",
    ]


DARS = Dars(
    kod='S10', nomi='Kechikkan zakaz', yonalish='sotuvchi', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi',
    vaziyat="Libos kecha qaytishi kerak edi. Tizim buni unutmaydi: zakaz qizil belgi bilan turadi, sizga va rahbarga eslatma "
            "boradi. Mijoz keldi — endi jarima masalasi. Uni siz emas, salon qoidasi hal qiladi.",
    natija="Kechikkan libosni qabul qilasiz va jarima qayerdan, qancha ushlanishini mijozga tushuntira olasiz.",
    xulosa=f"Qaytarish rasmiylashtirildi: tizim kechikkan kunni o'zi sanadi, {som(JARIMA)} jarimani garovdan ushladi va mijozga "
           f"{som(QAYTADI)} qaytarishni aytdi. Siz hech narsa hisoblamadingiz — shuning uchun mijoz bilan tortishuv ham yo'q: "
           "kunlik summa shartnomada yozilgan. Libos kechikayotgan kunlarda mijozga qo'ng'iroq qiling: bosh sahifadagi "
           "«Qo'ng'iroq qilish» ro'yxati shuni eslatadi. Agar salonda kechikish jarimasi o'chirilgan bo'lsa, tizim buni ochiq yozadi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=pul_oladimi,
    ishora="Kechikkan zakaz ham oddiy qaytarish kabi rasmiylashtiriladi — jarimani tizim o'zi qo'shadi.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
