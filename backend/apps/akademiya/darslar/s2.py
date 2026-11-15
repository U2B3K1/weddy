"""S2 — Libos kartasi va kalendar. Libos «salonda turibdi» degani «bo'sh» degani emas: kelgusi bronlari libos kartasidagi
pasportda (Katalog.jsx, Pasport), hamma liboslarning bandligi — Zakazlar → Bandlik kalendarida (Kalendar.jsx).
Tozalash kuni: bron qaytarish kunidan keyin yana `bufer_kun` kunni band qiladi (bookings.Bron.oraliq, standart 1 kun)."""
from datetime import date, timedelta

from apps.tenants.models import sozlama

from .asos import BAND_FIO, Dars, band_qil, holat_sanalari, katalog, nav, sana_matni, savollarni_tekshir, toy_sanalari

LIBOS = 'Atlas'


def urug(m):
    dan, gacha = toy_sanalari()
    l = katalog(m)
    band_qil(m, l['band'], dan, gacha)
    bufer = sozlama(m.salon).bufer_kun
    return {'dan': dan.isoformat(), 'gacha': gacha.isoformat(), 'bufer': bufer,
            'bosh': (gacha + timedelta(days=bufer + 1)).isoformat()}


def savollar(h):
    dan, gacha = holat_sanalari(h)
    bosh = date.fromisoformat(h['bosh'])
    ertasi = gacha + timedelta(days=1)
    return [
        {'matn': f"Yangi mijoz {LIBOS}ni {sana_matni(dan)} kuniga so'rayapti. Libos hozir javonda osilib turibdi. Nima deysiz?",
         'variantlar': [
             ('beraman', "Libos salonda-ku — yozaveraman", False,
              f"Javonda turgani bo'sh degani emas: «Kelgusi bronlar» da shu kunlar {BAND_FIO}ga yozilgan. Tizim ham ikkinchi bronni saqlamaydi."),
             ('band', "O'sha kunlarga band — boshqa libos yoki boshqa sana taklif qilaman", True,
              f"To'g'ri: pasportdagi «Kelgusi bronlar» da {LIBOS} shu kunlarga {BAND_FIO} nomiga band."),
             ('bekor', "Oldingi bronni bekor qilib, yangi mijozga beraman", False,
              "Birinchi mijoz avans bergan — uning broni mustahkam. Yangi mijozga boshqa libos yoki boshqa sana taklif qilinadi."),
         ]},
        {'matn': f"{LIBOS} {sana_matni(gacha)} kuni qaytadi. Uni eng erta qaysi kundan keyingi mijozga berish mumkin?",
         'variantlar': [
             ('oshakun', f"{sana_matni(gacha)} — qaytgan kuni kechqurun", False,
              "Qaytgan libos avval tozalanadi: tizim qaytarish kunidan keyin tozalash kunini ham band qilib qo'yadi."),
             ('ertasi', sana_matni(ertasi), False,
              f"{sana_matni(ertasi)} — tozalash kuni: libos hali tayyor emas, tizim bu kunga bron qo'ymaydi."),
             ('bosh', sana_matni(bosh), True,
              f"To'g'ri: {sana_matni(ertasi)} — tozalash kuni, {sana_matni(bosh)} dan libos yana bo'sh."),
         ]},
        {'matn': "Mijoz: «Shanba kuniga qaysi liboslaringiz bo'sh?» deb so'radi. Hammasini bir qarashda qayerdan ko'rasiz?",
         'variantlar': [
             ('birma', "Har bir libos kartasini birma-bir ochib chiqaman", False,
              "Bu juda uzoq. «Zakazlar → Bandlik kalendari» da hamma libos va hamma kun bitta jadvalda."),
             ('kalendar', "«Zakazlar» → «Bandlik kalendari»", True,
              "To'g'ri: u yerda har libos — bir qator, har kun — bir ustun. Bo'sh katakni bossangiz, o'sha libos va kunga yangi zakaz ochiladi."),
             ('hisobot', "«Hisobotlar» bo'limidan", False,
              "Hisobotlar o'tgan ishlar haqida. Bandlik — «Zakazlar → Bandlik kalendari» da."),
         ]},
    ]


def topshiriq(h):
    return (f"Mijozlar {LIBOS} libosini ko'p so'rashadi. Liboslar ro'yxatidan uning kartasini oching va «Kelgusi bronlar» ga qarab, "
            "uchta savolga javob bering.")


def tekshir(m, javob):
    return savollarni_tekshir(savollar(m.holat), javob)


def qadamlar(h):
    return ["Menyuda «Liboslar» ni oching.",
            f"Ro'yxatdan «{LIBOS}» kartasini bosing — ostida libos pasporti ochiladi.",
            "«Hozir» — libos qayerda; «Kelgusi bronlar» — qaysi kunlarga kimga yozilgan.",
            "Bron tugagan kunning ertasi — tozalash kuni: libos undan keyingi kundan bo'sh."]


def yol(h):
    return [nav('Liboslar'),
            {'matn': f"Ro'yxatdan «{LIBOS}» kartasini bosing.", 'amal': 'bos',
             'nishon': {'css': 'button.libos-karta', 'ichida': LIBOS}, 'tayyor': {'css': '.r2p-bronlar'}},
            {'matn': "Bu — libos pasporti. «Hozir» libos qayerdaligini, «Kelgusi bronlar» esa qaysi kunlarga kimga band ekanini "
                     f"ko'rsatadi. Bron tugagach libos yana {h['bufer']} kun tozalashda turadi — shundan keyingina bo'sh. "
                     "Savollarga javob bering.", 'amal': 'kor', 'nishon': {'css': '.r2p-pasport'}}]


def bilim(h):
    return [
        "Libos javonda turgani bo'sh degani emas: «Kelgusi bronlar» dagi kunlarga u band, tizim ikkinchi bronni saqlamaydi. "
        "Mijozga boshqa libos yoki boshqa sana taklif qilinadi.",
        f"Qaytgan libos darhol berilmaydi: qaytarish kunidan keyin {h['bufer']} kun tozalashda turadi, shundan keyingi kundan yana "
        "bo'sh.",
        "Hamma libosni bir qarashda ko'rish uchun — «Zakazlar» → «Bandlik kalendari»: har libos bir qator, har kun bir ustun.",
    ]


DARS = Dars(
    kod='S2', nomi='Libos kartasi va kalendar', yonalish='sotuvchi', personaj='madina',
    sahifa='Liboslar → libos kartasi',
    vaziyat="Mijoz aniq bir libosni yoqtirib qoldi va so'rayapti: «Shu qachon bo'sh?» Libos javonda osilib turgan bo'lishi mumkin, "
            "lekin kelasi shanbaga boshqa kelinga yozilgan. Javob — libos kartasida.",
    natija="Istalgan libosning qaysi kunlarga bandligini va qachondan bo'shligini ayta olasiz.",
    xulosa="Libos kartasi ikki savolga javob beradi: hozir qayerda va qaysi kunlarga band. Bron tugagach yana bir kun tozalashga "
           "ketadi — shuning uchun libos qaytgan kunning ertasiga va'da bermang. Bir nechta libosni solishtirish kerak bo'lsa — "
           "«Zakazlar → Bandlik kalendari»: hamma libos bitta jadvalda.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=savollar,
    ishora="Libos qayerda turgani emas, «Kelgusi bronlar» ro'yxati muhim.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
