"""S4 — Birinchi zakaz. Tekshiruv: mijoz nomiga to'g'ri sana va to'g'ri libos bilan zakaz yaratilganmi."""
from apps.orders.models import Zakaz, telefon_normal

from .asos import (LIBOSLAR_ROYXATI, MIJOZ_FIO, MIJOZ_TELEFON, Dars, holat_sanalari, kun, mezon, nav, sana_matni, tab,
                   toy_katalogi, tugma)


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    return {'dan': dan.isoformat(), 'gacha': gacha.isoformat(), 'liboslar': {k: v.id for k, v in l.items()}}


def topshiriq(h):
    dan, gacha = holat_sanalari(h)
    return (f"Mijoz {MIJOZ_FIO} (telefon {MIJOZ_TELEFON}) {sana_matni(dan)} kuni olib ketib, {sana_matni(gacha)} kuni "
            f"qaytarish uchun 44-o'lchamdagi milliy libos so'rayapti. Shu kunlarga bo'sh libosni topib, zakaz yarating.")


def tekshir(m, javob=None):
    h = m.holat
    dan, gacha = holat_sanalari(h)
    z = (Zakaz.objects.filter(salon=m.salon, mijoz__telefon=telefon_normal(MIJOZ_TELEFON))
         .exclude(holat=Zakaz.Holat.BEKOR).order_by('-id').first())
    if not z:
        boshqa = Zakaz.objects.filter(salon=m.salon, sotuvchi=m.xodim).exclude(holat=Zakaz.Holat.BEKOR).exists()
        return [mezon(False, '', f"Zakaz boshqa telefon raqamiga yozilgan. Mijoz raqami: {MIJOZ_TELEFON}." if boshqa
                      else f"{MIJOZ_FIO} nomiga zakaz hali yaratilmagan.")]
    l = h['liboslar']
    tanlangan = set(z.pozitsiyalar.values_list('libos_id', flat=True))
    if l['boshqa_olcham'] in tanlangan:
        libos_xato = "Tanlangan libos 46-o'lcham. Mijozga 44-o'lcham kerak."
    elif l['boshqa_toifa'] in tanlangan:
        libos_xato = "Tanlangan libos oq ko'ylak. Mijoz milliy libos so'ragan."
    else:
        libos_xato = "Zakazda bitta libos bo'lishi kerak: 44-o'lchamdagi milliy libos."
    return [
        mezon(z.olib_ketish == dan and z.qaytarish == gacha, "Sanalar to'g'ri.",
              f"Sanalar mos emas: zakazda {sana_matni(z.olib_ketish)} – {sana_matni(z.qaytarish)}, "
              f"kerak {sana_matni(dan)} – {sana_matni(gacha)}."),
        mezon(tanlangan == {l['togri']}, "Libos to'g'ri: 44-o'lcham, milliy, shu kunlarga bo'sh.", libos_xato),
        mezon(z.mijoz.fio.strip(), "Mijozning ismi yozilgan.",
              "Mijozning ismi yozilmagan — keyin uni faqat telefon raqamidan tanib bo'lmaydi."),
    ]


def qadamlar(h):
    dan, gacha = holat_sanalari(h)
    return ["Menyuda «Kassa» ni oching va tepadagi bo'limlardan «Yangi zakaz» ni tanlang.",
            f"Kalendarda {sana_matni(dan)} va {sana_matni(gacha)} kunlarini bosing, keyin «Davom etish — liboslarni tanlash».",
            "«Milliy» toifasida 44-o'lchamdagi libos kartasi ostidagi «Qo'shish» ni bosing. Libos qo'shilmaguncha «Davom etish» "
            "tugmasi ochilmaydi. Keyin «Davom etish» ni bosing.",
            f"«Mijoz telefoni» ga {MIJOZ_TELEFON}, «F.I.O.» ga {MIJOZ_FIO} deb yozing.",
            "«Zakazni saqlash» ni bosing."]


def yol(h):
    dan, gacha = holat_sanalari(h)
    return [nav('Kassa'), tab('Yangi zakaz'), kun(dan, 'olib ketish'), kun(gacha, 'qaytarish'),
            tugma('Davom etish — liboslarni tanlash', "Sanalar tanlandi. «Davom etish — liboslarni tanlash» ni bosing."),
            # tanlov o'quvchiniki: ro'yxatdagi istalgan libosni qo'sha oladi — to'g'risini o'zi topadi
            {'matn': "Mijozga mos libosni toping (milliy, 44-o'lcham) va uning ostidagi «Qo'shish» ni bosing.",
             'amal': 'bos', 'nishon': LIBOSLAR_ROYXATI, 'ichki': {'css': 'button', 'matn': "Qo'shish"}},
            tugma('Davom etish', "Libos zakazga qo'shildi. «Davom etish» ni bosing."),
            {'matn': f"Mijozning telefon raqamini yozing: {MIJOZ_TELEFON}.", 'amal': 'yoz',
             'nishon': {'css': 'input', 'placeholder': '+998'}, 'kutilgan': 'raqam:901234567'},
            {'matn': f"Mijoz yangi — ismini yozing: {MIJOZ_FIO}.", 'amal': 'yoz',
             'nishon': {'css': 'label:has(.majburiy) input'}, 'kutilgan': 'uzunlik:5'},
            tugma('Zakazni saqlash', "Hammasi tayyor. «Zakazni saqlash» ni bosing.")]


DARS = Dars(
    kod='S4', nomi='Birinchi zakaz', yonalish='sotuvchi', personaj='madina',
    sahifa='Kassa → Yangi zakaz',
    vaziyat="Mijoz qaror qildi: libosni oladi. Endi yo'lni oxirigacha o'tamiz: sana, libos va albatta mijozning o'zi — "
            "telefoni va ismi. Mijozsiz zakaz bo'lmaydi.",
    xulosa="Zakaz to'liq yo'l bilan yaratildi: sana → libos → mijoz. Har zakaz shu uch qadamdan iborat, mijoz ma'lumotisiz "
           "tizim saqlamaydi. Hozircha bu vaqtinchalik bron: avans olinmasa, 24 soatdan keyin o'zi bekor bo'ladi.",
    natija="Mijozga mos libosni topib, to'g'ri sanalar bilan zakaz yarata olasiz.",
    tekshirilgan='2026-11-12 · 1f405b7 dan keyingi ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir,
    ishora="Zakaz uch qadamda yaratiladi: sana → libos → mijoz. Keyingi qadam tugmasi oldingisi to'ldirilgach ochiladi: "
           "libos tanlash qadamida avval libosni «Qo'shish» bilan zakazga qo'shing.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
