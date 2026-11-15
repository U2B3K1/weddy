"""S11 — Sana yoki libosni almashtirish, bekor qilish. Uchalasi ham zakaz kartasidagi «Boshqa amallar» ichida
(Zakazlar.jsx KochirishForma, LibosAlmashtirishForma, BekorForma → orders/changes.py). Amalda sana ko'chiriladi va libos
almashtiriladi (bandlik va narx o'zi yangilanadi); bekor qilish — vaziyatli savollar bilan (o'quvchi zakazni buzib qo'ymasin)."""
from datetime import date, timedelta

from apps.bookings.models import Bron
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Libos
from apps.orders.models import Zakaz
from apps.orders.services import zakaz_yaratish

from .asos import (AVANS, BOSHQA_AMALLAR, IJARA, LIBOSLAR, MIJOZ_FIO, MIJOZ_TELEFON, TASDIQ_OYNASI, Dars, amal_bolimi,
                   holat_sanalari, kun, mezon, nav, pulchi, sana_matni, savollarni_tekshir, som, tasdiq, toy_katalogi, zakazni_och)

YANGI_NARX = 400_000
YANGI = LIBOSLAR['boshqa_toifa']  # O-001 Klassik — oq ko'ylak
OCHIQ_BOLIM = 'details.boshqa-amallar details.amal[open]'

SAVOLLAR = [
    {'matn': "Mijoz to'ydan voz kechdi va zakazni bekor qilmoqchi. Bergan avansidan qanchasi qaytadi?",
     'variantlar': [
         ('ozim', "O'zim kelishaman — yarmini qaytarsam bo'ladi", False,
          "Kelishish shart emas: salonning qaytarish qoidasi bor. «Zakazni bekor qilish» bo'limi aniq summani o'zi ko'rsatadi."),
         ('tizim', "«Zakazni bekor qilish» ni ochaman — tizim qoida bo'yicha aniq summani ko'rsatadi", True,
          "To'g'ri: qoida (to'yga necha kun qolganiga qarab) va qaytadigan summa bekor qilishdan oldin ekranda turadi."),
         ('qaytmaydi', "Avans hech qachon qaytmaydi", False,
          "Bu salon qoidasiga bog'liq: erta bekor qilinsa, avansning hammasi yoki bir qismi qaytadi. Tizim aniq summani ko'rsatadi."),
     ]},
    {'matn': "Zakazni bekor qilishdan oldin nimani bilishingiz kerak?",
     'variantlar': [
         ('qaytar', "Xato bo'lsa, keyin qayta tiklayman", False,
          "Tiklab bo'lmaydi: bekor qilingan zakaz qaytmaydi, libos esa darhol bo'shaydi. Kerak bo'lsa, yangi zakaz ochiladi."),
         ('sabab', "Sabab yoziladi va bekor qilingan zakaz qayta tiklanmaydi", True,
          "To'g'ri: sababsiz tizim bekor qilmaydi, amalning o'zi esa qaytarilmaydi — shuning uchun avval mijoz bilan aniqlashtiring."),
         ('rahbar', "Faqat rahbar bekor qila oladi", False,
          "Sotuvchi ham bekor qila oladi. Faqat «alohida kassir» tartibida to'lov qilingan zakazni kassir bekor qiladi — pul qaytarish kassada."),
     ]},
]


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    Libos.objects.filter(id=l['boshqa_toifa'].id).update(ijara_narxi=YANGI_NARX)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[l['togri'].id])
    p = pulchi(m)
    smena_ochish(salon=m.salon, xodim=p, boshlangich_qoldiq=0)
    tolov_qabul(salon=m.salon, xodim=p, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z)
    return {'zakaz': z.id, 'raqam': z.raqam, 'dan': dan.isoformat(), 'gacha': gacha.isoformat(),
            'yangi_dan': (dan + timedelta(days=7)).isoformat(), 'yangi_gacha': (gacha + timedelta(days=7)).isoformat(),
            'yangi_libos': l['boshqa_toifa'].id, 'eski_libos': l['togri'].id}


def yangi_sanalar(h):
    return date.fromisoformat(h['yangi_dan']), date.fromisoformat(h['yangi_gacha'])


def topshiriq(h):
    d, g = yangi_sanalar(h)
    return (f"{MIJOZ_FIO} qo'ng'iroq qildi (#{h['raqam']}-zakaz): to'y bir haftaga surilibdi — yangi kunlar {sana_matni(d)} – "
            f"{sana_matni(g)}. Yana bir o'zgarish: milliy libos o'rniga oq ko'ylak — {YANGI[0]} {YANGI[1]} ni olmoqchi. "
            "Zakazda avval sanani ko'chiring, keyin libosni almashtiring.")


def tekshir(m, javob=None):
    h = m.holat
    z = Zakaz.objects.filter(salon=m.salon, id=h['zakaz']).first()
    if not z or z.holat == Zakaz.Holat.BEKOR:
        return [mezon(False, '', "Zakaz bekor qilingan — mijoz esa faqat sana va libosni o'zgartirmoqchi edi. «Qayta boshlash» ni bosing.")]
    d, g = yangi_sanalar(h)
    liboslar = set(z.pozitsiyalar.values_list('libos_id', flat=True))
    band = set(Bron.objects.filter(salon=m.salon, zakaz=z).values_list('libos_id', flat=True))
    return [
        mezon((z.olib_ketish, z.qaytarish) == (d, g), f"Sana ko'chirildi: {sana_matni(d)} – {sana_matni(g)}.",
              f"Sana hali ko'chirilmagan: zakazda {sana_matni(z.olib_ketish)} – {sana_matni(z.qaytarish)}."),
        mezon(liboslar == {h['yangi_libos']}, f"Libos almashtirildi: {YANGI[0]} {YANGI[1]}.",
              "Libos hali almashtirilmagan." if liboslar == {h['eski_libos']} else f"Zakazda boshqa libos turibdi — kerak {YANGI[0]} {YANGI[1]}."),
        mezon(band == {h['yangi_libos']} and z.jami == YANGI_NARX,
              f"Bandlik va narx o'zi yangilandi: eski libos bo'shadi, jami {som(IJARA)} → {som(YANGI_NARX)}, avans joyida.",
              "Bandlik yoki narx hali yangilanmagan."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    d, g = yangi_sanalar(h)
    return ["Menyuda «Zakazlar» ni oching va mijozning zakazini bosing.",
            f"«Boshqa amallar» → «Sanani ko'chirish»: kalendarda {sana_matni(d)} va {sana_matni(g)} ni bosing, keyin «Ko'chirish» va tasdiq.",
            f"«Libosni almashtirish»: «Yangi libos» ro'yxatidan {YANGI[0]} {YANGI[1]} ni tanlang va «Almashtirish» ni bosing.",
            "Oxirida bekor qilish haqidagi ikkita savolga javob bering."]


def yol(h):
    d, g = yangi_sanalar(h)
    return [nav('Zakazlar'), zakazni_och(MIJOZ_FIO), BOSHQA_AMALLAR, amal_bolimi("Sanani ko'chirish"),
            kun(d, 'yangi olib ketish'), kun(g, 'yangi qaytarish'),
            {'matn': "Yangi kunlar tanlandi. «Ko'chirish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': f'{OCHIQ_BOLIM} button', 'matn': "Ko'chirish"}, 'tayyor': TASDIQ_OYNASI},
            tasdiq("Ha, ko'chirish", "Tizim eski va yangi sanalarni ko'rsatyapti. To'g'ri bo'lsa — «Ha, ko'chirish».",
                   tayyor={'css': '.karta-ong p.malumot', 'ichida': "Sana ko'chirildi"}),
            amal_bolimi('Libosni almashtirish', "Sana ko'chdi — libos yangi kunlarga band. Endi «Libosni almashtirish» ni oching."),
            {'matn': f"«Yangi libos» ro'yxatida faqat shu kunlarga bo'sh liboslar turadi. {YANGI[0]} {YANGI[1]} ni tanlang.",
             'amal': 'yoz', 'nishon': {'css': f'{OCHIQ_BOLIM} select', 'ichida': 'Tanlang'}, 'kutilgan': f"raqam:{h['yangi_libos']}"},
            {'matn': f"Tizim narx farqini ko'rsatdi: jami {som(IJARA)} → {som(YANGI_NARX)}. «Almashtirish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': f'{OCHIQ_BOLIM} button', 'matn': 'Almashtirish'},
             'tayyor': {'css': '.karta-ong p.malumot', 'ichida': 'Libos almashtirildi'}}]


def bilim(h):
    return [
        "Bekor qilish ham «Boshqa amallar» ichida: «Zakazni bekor qilish». Avansdan qanchasi qaytishini siz emas, salon qoidasi "
        "hal qiladi — tizim aniq summani bekor qilishdan oldin ko'rsatadi.",
        "Bekor qilish uchun sabab yoziladi. Bekor qilingan zakaz qayta tiklanmaydi — shuning uchun avval mijoz bilan aniqlashtiring.",
    ]


DARS = Dars(
    kod='S11', nomi='Sana yoki libosni almashtirish, bekor qilish', yonalish='sotuvchi', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi → Boshqa amallar',
    vaziyat="To'y sanasi surildi, kelin boshqa libosni yoqtirib qoldi yoki umuman voz kechdi — bunday qo'ng'iroqlar har hafta bo'ladi. "
            "Zakazni o'chirib, qaytadan yozish kerak emas: mavjud zakazning o'zi o'zgartiriladi, to'langan avans joyida qoladi.",
    natija="Zakazning sanasini ko'chirasiz, libosini almashtirasiz va bekor qilishda nima bo'lishini bilasiz.",
    xulosa="Ikkala o'zgarishda ham tizim ishning og'ir qismini o'zi qildi: yangi kunlarga libos bo'shligini tekshirdi, eski kunlarni "
           "va eski libosni bo'shatdi, narxni qayta hisobladi. Avans yo'qolmadi — qoldiq yangi narxdan hisoblanadi. Yangi kunlarga "
           "libos band bo'lsa, tizim ko'chirmaydi va sababini aytadi. Bekor qilish ham shu yerda — lekin u qaytarilmaydigan amal.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR,
    ishora="Zakazni o'chirmang: sana ham, libos ham zakaz kartasidagi «Boshqa amallar» ichida o'zgartiriladi.",
    qadamlar=qadamlar, yol=yol, xp=80,
)
