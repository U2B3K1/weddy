"""K2 — Bosh sahifa va bugungi ishlar. Kun shu savoldan boshlanadi: bugun kim keladi va kimdan qancha pul olinadi.
Sotuvchi va kassirda bu — bosh sahifadagi «Bugungi ishlar» jadvali (BoshEkran.jsx, XodimBosh); rahbarning bosh sahifasi —
ko'rsatkichlar paneli, bugungi ishlarni u Zakazlar ro'yxatidan ko'radi (har qatorda «bugun olib ketadi / qaytaradi»)."""
from datetime import timedelta

from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.orders.rental import libos_berish
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import Xodim

from .asos import (AVANS, BAND_FIO, BAND_TELEFON, GAROV, IJARA, MIJOZ_FIO, MIJOZ_TELEFON, Dars, katalog, nav, pulchi,
                   savollarni_tekshir, som, zakazni_och)

QOLDIQ = IJARA - AVANS

SAVOLLAR = [
    {'matn': "Bugun kim libosni olib ketadi?",
     'variantlar': [
         ('nilufar', MIJOZ_FIO, True, f"To'g'ri: {MIJOZ_FIO} bugun olib ketadi — uning zakazi «bron» holatida."),
         ('dilfuza', BAND_FIO, False, f"{BAND_FIO} libosni allaqachon olgan — u bugun qaytaradi."),
         ('hech', "Bugun hech kim olib ketmaydi", False, f"Ekranga qayta qarang: {MIJOZ_FIO} bugun olib ketadi."),
     ]},
    {'matn': f"{MIJOZ_FIO} kelganda undan ijara haqi uchun yana qancha olinadi?",
     'variantlar': [
         ('avans', som(AVANS), False, f"{som(AVANS)} — bu allaqachon olingan avans. Qolgani — {som(QOLDIQ)}."),
         ('qoldiq', som(QOLDIQ), True, f"To'g'ri: ijara {som(IJARA)}, avans {som(AVANS)} olingan — qoldiq {som(QOLDIQ)}."),
         ('jami', som(IJARA), False, f"{som(IJARA)} — butun ijara haqi. Undan {som(AVANS)} avans olingan, qoldiq {som(QOLDIQ)}."),
     ]},
    {'matn': "Ekran tepasidagi qo'ng'iroqcha (🔔) yonida son chiqdi. Bu nima?",
     'variantlar': [
         ('reklama', "Tizim yangiliklari — o'qimasa ham bo'ladi", False,
          "Yo'q: u yerda faqat ish — sizni kutayotgan zakaz, pul yoki qaror."),
         ('ish', "Meni kutayotgan ishlar: bosilsa, kerakli joy o'zi ochiladi", True,
          "To'g'ri: olib ketish, qaytarish, kechikkan zakaz, sizga topshirilgan pul — hammasi shu yerda va bosilsa o'sha joyga olib boradi."),
         ('xato', "Tizimdagi xatolar soni", False, "Xato emas — bu bugun sizdan kutilayotgan ishlar soni."),
     ]},
]


def urug(m):
    l = katalog(m)
    bugun = timezone.localdate()
    p = pulchi(m)
    smena_ochish(salon=m.salon, xodim=p, boshlangich_qoldiq=0)
    olib = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=bugun,
                          qaytarish=bugun + timedelta(days=2), libos_idlari=[l['togri'].id])
    tolov_qabul(salon=m.salon, xodim=p, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=olib)
    qaytar = zakaz_yaratish(salon=m.salon, xodim=m.hamkasb, telefon=BAND_TELEFON, fio=BAND_FIO, olib_ketish=bugun,
                            qaytarish=bugun, libos_idlari=[l['band'].id])
    tolov_qabul(salon=m.salon, xodim=p, tur=Tolov.Tur.AVANS, summa=qaytar.jami, zakaz=qaytar)
    libos_berish(salon=m.salon, xodim=p, zakaz=qaytar, zaloglar=[{'turi': 'pul', 'summa': GAROV}])
    return {'rahbar': m.xodim.rol == Xodim.Rol.RAHBAR}


def topshiriq(h):
    qayerda = "Zakazlar ro'yxati va zakaz kartasiga" if h.get('rahbar') else "Bosh sahifadagi «Bugungi ishlar» ga"
    return f"Ish kuni boshlandi. {qayerda} qarab, uchta savolga javob bering: bugun kim keladi va kimdan qancha pul olinadi."


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    if h.get('rahbar'):
        return ["Menyuda «Zakazlar» ni oching.",
                "Har zakazdagi belgiga qarang: «bugun olib ketadi», «bugun qaytaradi».",
                f"{MIJOZ_FIO}ning zakazini oching: «Qoldiq» — libos berilayotganda olinadigan pul."]
    return ["Menyuda «Dashboard» ni oching — bu sizning bosh sahifangiz.",
            "«Bugungi ishlar» jadvalida «Beriladi» va «Qaytadi» qatorlarini toping.",
            "«Qoldiq» ustuni mijozdan yana qancha olinishini ko'rsatadi."]


# Uchinchi savol qo'ng'iroqcha haqida — u ham ekranda ko'rsatiladi (savol ko'rsatilmagan narsani so'ramasin)
QONGIROQ = {'matn': "Avval tepaga qarang: qo'ng'iroqcha yonidagi son — sizni kutayotgan ishlar soni. Bosilsa, ro'yxati ochiladi va "
                    "har biri kerakli joyga olib boradi.", 'amal': 'kor', 'nishon': {'css': 'button.ustki-tugma', 'label': 'Bildirishnomalar'}}


def yol(h):
    if h.get('rahbar'):
        # Qoldiq zakaz kartasidan o'qiladi: telefonda ro'yxat kartasida summa yo'q, keng ekranda esa qisqartirilgan («0,1 / 0,3 mln»)
        return [nav('Zakazlar'), QONGIROQ,
                {'matn': "Bu — faol zakazlar. Har birida belgi bor: «bugun olib ketadi» yoki «bugun qaytaradi» — bugun kim kelishi "
                         "shundan bilinadi.", 'amal': 'kor', 'nishon': {'css': '.zakaz-jadval, .zt-royxat'}},
                zakazni_och(MIJOZ_FIO, f"Endi pulni ko'ramiz. {MIJOZ_FIO}ning zakazini oching."),
                {'matn': "Hisobga qarang: «To'langan» — olingan avans, «Qoldiq» — mijozdan yana olinadigan pul. "
                         "Savollarga javob bering.", 'amal': 'kor', 'nishon': {'css': 'dl.varaq-hisob:has(> .varaq-qoldiq)'}}]
    return [nav('Dashboard'), QONGIROQ,
            {'matn': "Bu — bugungi ishlaringiz. «Beriladi» — mijoz libosni olib ketadi, «Qaytadi» — qaytaradi; yonidagi summa — "
                     "mijozdan yana olinadigan qoldiq. Qarab chiqing va savollarga javob bering.", 'amal': 'kor',
             'nishon': {'css': '#ish-bugun'}}]


DARS = Dars(
    kod='K2', nomi='Bosh sahifa va bugungi ishlar', yonalish='kirish', personaj='madina',
    sahifa='Bosh sahifa · Zakazlar',
    vaziyat="Ertalab ilovani ochdingiz. Birinchi savol har doim bitta: bugun kim keladi? Kim libos olib ketadi, kim qaytaradi, "
            "kimdan pul olinadi — buni eslab yurish shart emas, tizim o'zi ko'rsatadi.",
    natija="Ish kunini bugungi ishlar ro'yxatidan boshlaysiz: kim keladi va kimdan qancha olinishini bir qarashda aytasiz.",
    xulosa="Kun shu ro'yxatdan boshlanadi. Sotuvchi va kassirda u bosh sahifada turadi, har qatorda keyingi amal tugmasi bor: "
           "«To'lov va berish», «Qabul qilish». Rahbar bosh sahifasida salon ko'rsatkichlarini ko'radi, bugungi ishlarni esa "
           "«Zakazlar» da. Ikkalasida ham qo'ng'iroqcha bir xil ishlaydi: son — sizni kutayotgan ishlar.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR,
    ishora="Har zakazda uchta narsaga qarang: kim, bugun nima qiladi (oladi yoki qaytaradi) va qancha pul qolgan.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
