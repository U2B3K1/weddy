"""R5B — Kim libos qo'shadi va artikul (rahbar). Sozlama → «Liboslar» guruhi: «Libos qo'shish va manekin»
(`sotuvchi_libos_qoshadi`, `manekin`) va «Libos artikuli» (`artikul_avto`, `artikul_prefiks`, `artikul_boshlanish`, `artikul_xona`)
bitta sahifada. Keyingi artikul: prefiks + raqam, xonalar soni bo'yicha nol bilan to'ldiriladi (catalog/services.keyingi_artikul)."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

PREFIKS = 'L-'

SAVOLLAR = [
    {'matn': f"Prefiks «{PREFIKS}», sanoq 1 dan, raqam 4 xonali. Salonda hali libos yo'q. Birinchi qo'shilgan libos artikuli qanday bo'ladi?",
     'variantlar': [
         ('bir', f"{PREFIKS}1", False, "Raqam 4 xonali qilib nol bilan to'ldiriladi: L-0001."),
         ('togri', f"{PREFIKS}0001", True,
          "To'g'ri: prefiks + 4 xonali raqam. Keyingilari L-0002, L-0003… Ikki xodim bir vaqtda qo'shsa ham takrorlanmaydi."),
         ('bosh', "Artikulni har safar o'zim yozaman", False,
          "Avtomatik raqam yoqilgan bo'lsa, artikul maydoni bo'sh qoldiriladi — tizim keyingisini o'zi beradi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return ("Katalog tartibsiz bo'lib ketdi: sotuvchilar har xil artikul yozyapti, ba'zan narxsiz libos qo'shishyapti. Ikki qaror: "
            f"1) bundan buyon libosni faqat siz qo'shasiz; 2) artikulni tizim o'zi beradi — «{PREFIKS}» bilan boshlanib.")


def tekshir(m, javob=None):
    s = sozlama(m.salon)
    return [
        mezon(not s.sotuvchi_libos_qoshadi, "Endi libosni faqat rahbar qo'shadi.",
              "Sotuvchilar hali ham libos qo'sha oladi. Almashtirgichni o'chirib, «Saqlash» ni bosing."),
        mezon(s.artikul_avto, "Artikul raqami avtomatik qo'yiladi.",
              "Avtomatik artikul hali o'chiq. «Raqam avtomatik qo'yilsin» ni yoqib, «Saqlash» ni bosing."),
        mezon(s.artikul_prefiks.upper() == PREFIKS, f"Prefiks — «{PREFIKS}».",
              f"Prefiks «{s.artikul_prefiks}» — «{PREFIKS}» bo'lishi kerak."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Libos qo'shish va manekin» bo'limiga kiring.",
            "«Sotuvchi libos va aksessuar qo'sha oladi» ni o'chiring.",
            f"Pastdagi «Libos artikuli» da «Raqam avtomatik qo'yilsin» ni yoqing, «Prefiks» ga {PREFIKS} yozing.",
            "«Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori("Libos qo'shish va manekin"),
            {'matn': "«Sotuvchi libos va aksessuar qo'sha oladi» yoqilgan. Uni o'chiring — libosni faqat siz qo'shasiz.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': "Sotuvchi libos va aksessuar qo'sha oladi"}, 'tayyor': {'css': '.sozlama-saqlash'}},
            {'matn': "Shu sahifaning pastida — «Libos artikuli». «Raqam avtomatik qo'yilsin» ni yoqing.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': "Raqam avtomatik qo'yilsin"},
             'tayyor': {'css': 'input', 'label': 'Sanoq nechidan boshlansin'}},
            {'matn': f"«Prefiks» ga yozing: {PREFIKS}. Har artikul shu bilan boshlanadi.", 'amal': 'yoz',
             'nishon': {'css': 'input', 'label': 'Artikul prefiksi'}, 'kutilgan': 'matn:l-'},
            {**SAQLASH, 'matn': "Ikkala o'zgarish bitta «Saqlash» bilan kuchga kiradi. Pastdagi «Saqlash» ni bosing."}]


def bilim(h):
    return [
        "Artikul = prefiks + raqam. Raqam 4 xonali bo'lib, oldi nol bilan to'ldiriladi: masalan «A-» prefiksi bilan uchinchi libos — "
        "A-0003. Libos qo'shishda artikul maydoni bo'sh qoldiriladi — tizim o'zi beradi.",
    ]


DARS = Dars(
    kod='R5B', nomi="Kim libos qo'shadi va artikul", yonalish='rahbar', personaj='nodira',
    sahifa="Sozlama → Libos qo'shish va manekin · Libos artikuli",
    vaziyat="Artikul — libosning yorlig'idagi kod: sanoq, zakaz va hisobot shu bilan ishlaydi. Har kim o'zicha yozsa, ikkita «A12» "
            "paydo bo'ladi. Katalogga kim libos qo'shishini ham shu yerda hal qilasiz.",
    natija="Katalogga kim libos qo'shishini belgilaysiz va artikul raqamlashni avtomatik qilasiz.",
    xulosa=f"Endi libosni faqat siz qo'shasiz, artikulni esa tizim beradi: {PREFIKS}0001, {PREFIKS}0002… Libos qo'shishda artikul "
           "maydonini bo'sh qoldirasiz. Sotuvchilarga qo'shishni qayta ochsangiz ham, ular qo'shgan libos siz narx va tannarxni "
           "tasdiqlamaguncha katalogga chiqmaydi. Shu bo'limdagi «Raqamli manekin» — libosni manekinda ko'rsatish; ixtiyoriy, "
           "oddiy rasm ham yetadi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Ikkala sozlama «Liboslar» guruhida, bitta sahifada.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
