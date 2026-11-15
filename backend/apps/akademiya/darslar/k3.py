"""K3 — To'rt xil pul: ijara, avans, qoldiq, garov. Bitta zakaz misolida ko'rsatiladi (zakaz kartasi, Zakazlar.jsx Karta):
ijara haqi = avans + qoldiq — salon daromadi; garov alohida yoziladi va mijozga qaytadi (rental.py; hisobotlarda daromad emas)."""
from datetime import timedelta

from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.orders.rental import libos_berish
from apps.orders.services import zakaz_yaratish

from .asos import (AVANS, GAROV, IJARA, MIJOZ_FIO, MIJOZ_TELEFON, Dars, katalog, nav, pulchi, savollarni_tekshir, som,
                   zakazni_och)

QOLDIQ = IJARA - AVANS

SAVOLLAR = [
    {'matn': "Shu zakazdan salon qancha ishladi (daromad)?",
     'variantlar': [
         ('avans', som(AVANS), False, f"{som(AVANS)} — faqat avans. Ijara haqi to'liq: avans + qoldiq = {som(IJARA)}."),
         ('ijara', som(IJARA), True, f"To'g'ri: daromad — ijara haqi, ya'ni avans {som(AVANS)} + qoldiq {som(QOLDIQ)}."),
         ('hammasi', som(IJARA + GAROV), False,
          f"Garov {som(GAROV)} daromad emas — u mijozning puli va libos qaytganda qaytariladi. Daromad — {som(IJARA)}."),
     ]},
    {'matn': f"Garov {som(GAROV)} — bu kimning puli?",
     'variantlar': [
         ('salon', "Salonniki — libos uchun qo'shimcha to'lov", False,
          "Yo'q: garov to'lov emas. Libos butun qaytsa, mijozga to'liq qaytariladi."),
         ('mijoz', "Mijozniki — libos butun qaytsa, qaytariladi", True,
          "To'g'ri: garov seyfda saqlanadi. Faqat libosga zarar yetsa yoki kech qaytsa, jarima shundan ushlanadi."),
         ('sotuvchi', "Sotuvchiniki — xizmat haqi", False, "Garov hech kimning xizmat haqi emas — u mijozga qaytadigan pul."),
     ]},
    {'matn': "Avans nima?",
     'variantlar': [
         ('garov', "Garovning boshqa nomi", False,
          "Avans va garov — ikki xil pul. Avans — ijara haqining bir qismi, garov — kafolat (libos qaytganda qaytadi)."),
         ('qism', "Ijara haqining oldindan olingan qismi — bronni mustahkamlaydi", True,
          "To'g'ri: avans olingach libos shu mijozga band bo'ladi. Qolgani (qoldiq) libos berilayotganda olinadi."),
         ('ustama', "Ijara haqi ustiga qo'shimcha to'lov", False,
          "Avans qo'shimcha emas — u ijara haqining ichida: avans + qoldiq = ijara haqi."),
     ]},
    {'matn': "Libos mijozning qo'liga berilishidan oldin nima bo'lishi shart?",
     'variantlar': [
         ('avans', "Avans olingan bo'lsa yetarli", False,
          "Yetmaydi: tizim qoldiq to'lanmaguncha va garov olinmaguncha libosni berdirmaydi."),
         ('ikkalasi', "Qoldiq to'liq to'langan va garov olingan", True,
          "To'g'ri: avval qoldiq, keyin garov — shundan keyingina libos beriladi."),
         ('garov', "Faqat garov — qoldiqni qaytarganda oladi", False,
          "Yo'q: ijara haqi libos berilguncha to'liq olinadi. Qaytarganda faqat garov bilan hisob-kitob qilinadi."),
     ]},
]


def urug(m):
    l = katalog(m)
    bugun = timezone.localdate()
    p = pulchi(m)
    smena_ochish(salon=m.salon, xodim=p, boshlangich_qoldiq=0)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=bugun,
                       qaytarish=bugun + timedelta(days=2), libos_idlari=[l['togri'].id])
    tolov_qabul(salon=m.salon, xodim=p, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z)
    tolov_qabul(salon=m.salon, xodim=p, tur=Tolov.Tur.QOLDIQ, summa=QOLDIQ, zakaz=z)
    libos_berish(salon=m.salon, xodim=p, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': GAROV}])
    return {'raqam': z.raqam}


def topshiriq(h):
    return (f"{MIJOZ_FIO}ning #{h['raqam']}-zakazini oching. Unda to'rt xil pul bor: ijara haqi, avans, qoldiq va garov. "
            "«To'lovlar» ro'yxatiga qarab, to'rtta savolga javob bering.")


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Zakazlar» ni oching va mijozning zakazini bosing.",
            "Varaqda «Jami» — ijara haqi. «To'lovlar» ro'yxatida avans va qoldiq alohida yozilgan — yig'indisi «Jami» ga teng.",
            "Garov alohida qatorda va «saqlanmoqda» deb turibdi: u ijara haqiga qo'shilmaydi."]


def yol(h):
    return [nav('Zakazlar'), zakazni_och(MIJOZ_FIO),
            # nomlar ekrandagidek: «Avans», «Qoldiq to'lov», «Garov» (varaqdagi «Qoldiq 0 so'm» bilan adashtirilmasin)
            {'matn': f"«To'lovlar» blokida uch qator bor. «Avans» {som(AVANS)} va «Qoldiq to'lov» {som(QOLDIQ)} — ikkalasi birga "
                     f"ijara haqi. «Garov» {som(GAROV)} alohida turibdi: «saqlanmoqda». Savollarga javob bering.", 'amal': 'kor',
             'nishon': {'css': '.karta-tolovlar'}}]


def bilim(h):
    return [
        "Ijara haqi — libos uchun to'lov, salonning daromadi shu. Mijoz uni ikki bo'lib beradi: avans va qoldiq.",
        "Avans — ijara haqining oldindan olinadigan qismi. Avans olingach bron mustahkamlanadi: libos shu mijozga band.",
        "Qoldiq — ijara haqining qolgan qismi. U libos berilayotgan kuni olinadi.",
        "Garov — kafolat puli, u mijozniki: seyfda saqlanadi va libos butun qaytsa to'liq qaytariladi. Daromadga qo'shilmaydi; "
        "jarima bo'lsa, shundan ushlanadi.",
        "Berish tartibi: avval qoldiq to'liq to'lanadi, keyin garov olinadi — shundan keyingina libos beriladi. Tizim boshqacha "
        "berdirmaydi.",
    ]


DARS = Dars(
    kod='K3', nomi="To'rt xil pul: ijara, avans, qoldiq, garov", yonalish='kirish', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi',
    vaziyat="Bitta zakazda mijoz salonga uch marta pul beradi va bir marta qaytarib oladi. Bu pullarni aralashtirsangiz, kassa "
            "to'g'ri kelmaydi va mijoz bilan tortishuv chiqadi. Shuning uchun avval nomlarini aniq bilib olamiz.",
    natija="Ijara haqi, avans, qoldiq va garovni bir-biridan ajratasiz va qaysi biri salon daromadi ekanini bilasiz.",
    xulosa="Formulasi oddiy: ijara haqi = avans + qoldiq — bu salon daromadi. Garov — alohida pul: mijozniki, seyfda turadi va "
           "libos butun qaytsa qaytariladi. Tizim garovni hech qachon tushumga qo'shmaydi — smena hisobotida ham, oylik foydada ham.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR,
    ishora="Har bir pul haqida o'ylang: u salonda qoladimi yoki mijozga qaytadimi?",
    qadamlar=qadamlar, yol=yol, xp=50,
)
