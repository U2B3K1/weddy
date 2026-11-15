"""R7 — Narx: tayyor chegirma, promokod, mavsumiy ustama (rahbar). Amalda bitta tayyor chegirma qo'shiladi,
qolgan ikki vosita vaziyat orqali o'rgatiladi. Qoidalar kod bilan solishtirilgan: TayyorChegirma (FT-11.7 — ro'yxatdagi
chegirma tasdiqsiz, boshqasi rahbar tasdig'iga), pricing.mavsumiy_foiz (olib ketish kuniga qarab, eng katta foiz),
SalonSozlamalari.promokod_chegirma_birga (standart — o'chiq)."""
from apps.orders.models import TayyorChegirma

from .asos import Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

NOM, FOIZ = 'Doimiy mijoz', 10
FORMA = '.soz-qosh'

SAVOLLAR = [
    {'matn': "Sotuvchi mijozga ro'yxatda yo'q chegirma — 25% — bermoqchi. Nima bo'ladi?",
     'variantlar': [
         ('darhol', "Tizim chegirmani darhol qo'llaydi", False,
          "Darhol faqat siz oldindan qo'shgan tayyor chegirmalar qo'llanadi. Ro'yxatda yo'g'i sizning tasdig'ingizga keladi."),
         ('tasdiq', "So'rov menga tasdiqqa keladi", True,
          "To'g'ri: ro'yxatdagi chegirmani sotuvchi bir bosishda beradi, boshqasini esa siz tasdiqlaysiz."),
         ('taqiq', "Tizim bunday chegirmaga umuman yo'l qo'ymaydi", False,
          "Yo'l qo'yadi, lekin tasdiq bilan: so'rov sizga keladi va siz hal qilasiz."),
     ]},
    {'matn': "Iyun–avgust — to'y mavsumi: shu kunlarga olinadigan liboslar 20% qimmat bo'lishi kerak. Qanday qilasiz?",
     'variantlar': [
         ('qolda', "Har libosning narxini 20% oshirib chiqaman, kuzda qaytaraman", False,
          "Buning keragi yo'q: «Mavsumiy narx» qoidasi ustamani zakazga o'zi qo'shadi, libos narxi o'zgarmaydi."),
         ('mavsumiy', "«Mavsumiy narx» ni yoqib, iyun–avgustga 20% ustama qoidasini qo'shaman", True,
          "To'g'ri: ustama olib ketish kuniga qarab o'zi qo'shiladi. Bir kunga ikki qoida to'g'ri kelsa — kattasi olinadi."),
         ('sotuvchi', "Sotuvchilarga aytaman: zakazda narxni qo'lda oshirsin", False,
          "Odam unutadi yoki adashadi. «Mavsumiy narx» qoidasi buni har zakazda o'zi qiladi."),
     ]},
    {'matn': "Mijoz «KELIN10» promokodi bilan keldi va ustiga «Doimiy mijoz» chegirmasini ham so'rayapti. "
             "Standart sozlamada nima bo'ladi?",
     'variantlar': [
         ('ikkala', "Ikkalasi qo'shilib, 20% bo'ladi", False,
          "Standart holatda qo'shilmaydi: bittasi tanlanadi. Birga berish uchun «Promokod va qo'shimcha chegirma birga» ni yoqasiz."),
         ('bitta', "Bittasi tanlanadi — salon ikki marta chegirma bermaydi", True,
          "To'g'ri. Ikkalasini birga bermoqchi bo'lsangiz — Promokodlar bo'limida «Promokod va qo'shimcha chegirma birga» ni yoqasiz."),
         ('saqlanmaydi', "Tizim zakazni saqlamaydi", False,
          "Zakaz saqlanadi — faqat ikki chegirmadan bittasi tanlanadi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Sotuvchilar doimiy mijozlarga chegirma berish uchun har safar sizga qo'ng'iroq qilyapti. "
            f"Tayyor chegirma qo'shing: nomi «{NOM}», {FOIZ}% — shundan keyin ular uni o'zlari bera oladi.")


def tekshir(m, javob=None):
    hammasi = TayyorChegirma.objects.filter(salon=m.salon, faol=True)
    mos = hammasi.filter(foiz=FOIZ).first()
    if mos:
        natija = [mezon(True, f"Tayyor chegirma qo'shildi: «{mos.nomi}» · {FOIZ}%.", '')]
    elif hammasi.exists():
        natija = [mezon(False, '', f"Chegirma qo'shilgan, lekin {FOIZ}% emas. Turi «Foiz, %», qiymati {FOIZ} bo'lishi kerak.")]
    else:
        natija = [mezon(False, '', "Tayyor chegirma hali qo'shilmagan.")]
    return natija + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Tayyor chegirmalar» bo'limiga kiring.",
            "«Chegirma qo'shish» ni bosing.",
            f"Nomiga «{NOM}» deb yozing, turi «Foiz, %» tursin, qiymatiga {FOIZ} yozing va «Qo'shish» ni bosing.",
            "Pastdagi uchta savolga javob bering."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Tayyor chegirmalar'),
            {'matn': "«Chegirma qo'shish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': 'main button', 'matn': "Chegirma qo'shish"}, 'tayyor': {'css': f'{FORMA} input', 'label': 'Chegirma nomi'}},
            {'matn': f"Nomini yozing: {NOM}. Sotuvchi zakazda aynan shu nomni ko'radi.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} input', 'label': 'Chegirma nomi'}, 'kutilgan': 'uzunlik:5'},
            {'matn': f"Turi «Foiz, %» turibdi. Qiymatini yozing: {FOIZ}.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} input', 'label': 'Qiymat'}, 'kutilgan': f'raqam:{FOIZ}'},
            {'matn': "«Qo'shish» ni bosing.", 'amal': 'bos', 'nishon': {'css': f'{FORMA} button', 'matn': "Qo'shish"},
             'tayyor': {'css': '#soz-chegirmalar .soz-izoh', 'ichida': "qo'shildi"}}]


def bilim(h):
    return [
        "Ro'yxatdagi (tayyor) chegirmani sotuvchi tasdiqsiz, bir bosishda beradi. Ro'yxatda yo'q chegirmani ham so'rashi mumkin — "
        "lekin u sizga tasdiqqa keladi.",
        "Mavsumda narxlarni qo'lda oshirmaysiz: «Mavsumiy narx» da sanalar oralig'iga ustama qoidasi qo'shiladi. U zakazga olib "
        "ketish kuniga qarab o'zi qo'shiladi.",
        "Promokod va chegirma standart holatda qo'shilmaydi: bittasi tanlanadi. Birga berish kerak bo'lsa — Promokodlar bo'limida "
        "alohida yoqiladi.",
    ]


DARS = Dars(
    kod='R7', nomi='Narx: chegirma, promokod, mavsumiy ustama', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Narx va chegirma',
    vaziyat="Narxni kim o'zgartira oladi? Agar har chegirma uchun sizga qo'ng'iroq qilinsa — mijoz kutadi; agar sotuvchi "
            "xohlaganicha chegirma bersa — foyda ketadi. Tizimda buning o'rtasi bor: chegaralarni bir marta siz belgilaysiz.",
    natija="Tayyor chegirma qo'sha olasiz va narxni o'zgartiradigan uch vositani bir-biridan ajratasiz.",
    xulosa=f"Uch vosita: «Tayyor chegirmalar» — sotuvchi tasdiqsiz beradi (hozir «{NOM}» ni qo'shdingiz), ro'yxatda yo'g'i "
           "sizga tasdiqqa keladi; «Promokodlar» — aksiya yoki salonchi kodi, standart holatda chegirma bilan qo'shilmaydi; "
           "«Mavsumiy narx» — to'y mavsumidagi ustama, zakazga olib ketish kuniga qarab o'zi qo'shiladi. Uchalasi ham "
           "«Sozlama → Narx va chegirma» da.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Sotuvchi tasdiqsiz bera oladigan chegirmalar «Sozlama → Tayyor chegirmalar» da qo'shiladi.",
    qadamlar=qadamlar, yol=yol, xp=70,
)
