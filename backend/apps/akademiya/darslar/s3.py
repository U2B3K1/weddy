"""S3 — Mijozni topish yoki qo'shish. Qaytgan mijoz «Mijozlar» bo'limidan topiladi va kartasidagi «Yangi zakaz» bilan
davom etiladi: telefon va ism o'zi to'ladi (Mijozlar.jsx Karta → YangiZakaz boshlangich). Mijoz telefon raqami bo'yicha
bitta — yangi yozuv faqat boshqa raqam terilganda paydo bo'ladi (orders.services.zakaz_yaratish: get_or_create)."""
from datetime import timedelta

from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Libos
from apps.orders.models import Mijoz, Zakaz, telefon_normal
from apps.orders.rental import libos_berish, libos_qaytarish
from apps.orders.services import zakaz_yaratish

from .asos import (BAND_TELEFON, GAROV, LIBOSLAR_ROYXATI, MIJOZ_FIO, MIJOZ_TELEFON, Dars, band_qil, holat_sanalari, katalog, kun, mezon,
                   nav, otgan_sanaga, pulchi, sana_matni, toy_sanalari, tugma)

ISM = MIJOZ_FIO.split()[0]


def urug(m):
    """Nilufar ikki oy oldin libos olib, qaytargan: kartasida bitta yopilgan zakaz bor."""
    dan, gacha = toy_sanalari()
    l = katalog(m)
    band_qil(m, l['band'], dan, gacha)
    bugun = timezone.localdate()
    p = pulchi(m)
    smena_ochish(salon=m.salon, xodim=p, boshlangich_qoldiq=0)
    eski = zakaz_yaratish(salon=m.salon, xodim=m.hamkasb, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=bugun,
                          qaytarish=bugun, libos_idlari=[l['togri'].id])
    tolov_qabul(salon=m.salon, xodim=p, tur=Tolov.Tur.AVANS, summa=eski.jami, zakaz=eski)
    libos_berish(salon=m.salon, xodim=p, zakaz=eski, zaloglar=[{'turi': 'pul', 'summa': GAROV}])
    libos_qaytarish(salon=m.salon, xodim=p, zakaz=eski)
    otgan_sanaga(eski, bugun - timedelta(days=60), bugun - timedelta(days=58))
    Libos.objects.filter(id=l['togri'].id).update(holat=Libos.Holat.BOSH)  # tozalash allaqachon tugagan
    return {'dan': dan.isoformat(), 'gacha': gacha.isoformat(), 'mijoz': eski.mijoz_id, 'eski': eski.id,
            'liboslar': {k: v.id for k, v in l.items()}}


def topshiriq(h):
    dan, gacha = holat_sanalari(h)
    return (f"{MIJOZ_FIO} ikki oy oldin sizdan libos olgan edi. Bugun singlisining to'yi uchun yana keldi: {sana_matni(dan)} – "
            f"{sana_matni(gacha)}, yana 44-o'lchamdagi milliy libos. Uni «Mijozlar» dan toping va kartasidan yangi zakaz oching.")


def tekshir(m, javob=None):
    h = m.holat
    dan, gacha = holat_sanalari(h)
    z = (Zakaz.objects.filter(salon=m.salon).exclude(id=h['eski']).exclude(holat=Zakaz.Holat.BEKOR)
         .exclude(mijoz__telefon=telefon_normal(BAND_TELEFON)).order_by('-id').first())
    if not z:
        return [mezon(False, '', f"{MIJOZ_FIO} uchun yangi zakaz hali yaratilmagan.")]
    tanlangan = set(z.pozitsiyalar.values_list('libos_id', flat=True))
    nusxa = Mijoz.objects.filter(salon=m.salon, fio__icontains=ISM).count()
    return [
        mezon(z.mijoz_id == h['mijoz'] and nusxa == 1, f"Zakaz mavjud mijozga yozildi — {ISM} tizimda bitta.",
              f"Zakaz boshqa telefon raqamiga yozilgan: tizimda endi ikkita «{ISM}» bor va uning tarixi ikkiga bo'lindi. "
              "«Qayta boshlash» ni bosib, mijozni kartasidan oching."),
        mezon(z.olib_ketish == dan and z.qaytarish == gacha, "Sanalar to'g'ri.",
              f"Sanalar mos emas: kerak {sana_matni(dan)} – {sana_matni(gacha)}."),
        mezon(tanlangan == {h['liboslar']['togri']}, "Libos to'g'ri: milliy, 44-o'lcham.",
              "Zakazda bitta libos bo'lishi kerak: 44-o'lchamdagi milliy libos."),
    ]


def qadamlar(h):
    dan, gacha = holat_sanalari(h)
    return ["Menyuda «Mijozlar» ni oching va qidiruvga «Nilufar» deb yozing.",
            "Chiqqan qatorni bosing — mijoz kartasi ochiladi: oldingi zakazi shu yerda.",
            "Kartaning tepasidagi «Yangi zakaz» ni bosing — telefon va ism yangi zakazga o'zi o'tadi.",
            f"Sanalarni tanlang: {sana_matni(dan)} va {sana_matni(gacha)}, keyin mos libosni qo'shing.",
            "Oxirgi qadamda tizim «Mavjud mijoz» deb ko'rsatadi — «Zakazni saqlash» ni bosing."]


def yol(h):
    dan, gacha = holat_sanalari(h)
    return [nav('Mijozlar'),
            {'matn': f"Qidiruvga mijozning ismini yozing: {ISM}.", 'amal': 'yoz',
             'nishon': {'css': 'input.jadval-qidiruv', 'label': 'Mijoz qidirish'}, 'kutilgan': f'matn:{ISM[:4].lower()}'},
            {'matn': f"{MIJOZ_FIO} topildi. Qatorni bosib, kartasini oching.", 'amal': 'bos',
             'nishon': {'css': 'tbody tr, button.mt-qator', 'ichida': MIJOZ_FIO}, 'tayyor': {'css': 'button.r2m-yangi'}},
            {'matn': "Bu — mijoz kartasi: oldingi zakazi va to'lovlari shu yerda. Tepadagi «Yangi zakaz» ni bosing — "
                     "telefon va ism o'zi o'tadi.", 'amal': 'bos', 'nishon': {'css': 'button.r2m-yangi'}},
            kun(dan, 'olib ketish'), kun(gacha, 'qaytarish'),
            tugma('Davom etish — liboslarni tanlash', "Sanalar tanlandi. «Davom etish — liboslarni tanlash» ni bosing."),
            {'matn': "Mijozga mos libosni toping (milliy, 44-o'lcham) va «Qo'shish» ni bosing.", 'amal': 'bos',
             'nishon': LIBOSLAR_ROYXATI, 'ichki': {'css': 'button', 'matn': "Qo'shish"}},
            tugma('Davom etish', "Libos qo'shildi. «Davom etish» ni bosing."),
            tugma('Zakazni saqlash', "Telefon va ism o'zi to'lgan, tizim uni «Mavjud mijoz» deb tanidi — hech narsa termaysiz. "
                                     "«Zakazni saqlash» ni bosing.")]


DARS = Dars(
    kod='S3', nomi="Mijozni topish yoki qo'shish", yonalish='sotuvchi', personaj='madina',
    sahifa='Mijozlar → mijoz kartasi → Yangi zakaz',
    vaziyat="Eshikdan tanish yuz kirdi — bu mijoz sizdan avval ham libos olgan. Uni yangi mijoz qilib qayta yozsangiz, tizimda "
            "ikkita «Nilufar» paydo bo'ladi: tarixi bo'linadi, «doimiy mijoz» ekani ko'rinmay qoladi.",
    natija="Qaytgan mijozni topib, uning kartasidan yangi zakaz ochasiz — takror yozuv yaratmaysiz.",
    xulosa="Mijoz tizimda telefon raqami bilan taniladi. Shuning uchun ikki yo'l ham to'g'ri: kartasidan «Yangi zakaz» ni bosish "
           "yoki yangi zakazda o'sha raqamni terish — tizim «Mavjud mijoz» deb ko'rsatadi. Yangi mijoz esa alohida qo'shilmaydi: "
           "yangi raqam terilganda tizim ismini so'raydi va zakaz bilan birga o'zi yaratadi. Mijoz raqamini almashtirgan bo'lsa — "
           "yangisini kartasidagi «Qo'shimcha telefon» ga yozing, yangi mijoz ochmang.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir,
    ishora="Avval «Mijozlar» dan qidiring. Topilsa — zakazni uning kartasidan boshlang.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
