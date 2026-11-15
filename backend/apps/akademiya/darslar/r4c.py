"""R4C — Filiallar (rahbar). Sozlama → «Filiallar» (Sozlamalar.jsx `filiallar`, tenants/views_filial.py): filial qo'shiladi;
faol filial bo'lsa «Har filialda alohida kassa» chiqadi (SalonSozlamalari.filial_kassasi). Zakaz qurilma biriktirilgan
filialga yoziladi — qurilma Sozlama → «Qurilmalar va parol» → «Filial» bilan biriktiriladi (QurilmaQator)."""
from apps.tenants.models import Filial, sozlama

from .asos import SAQLASH, SAQLANDI, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

NOMI, MANZIL = 'Chilonzor', 'Chilonzor 9-kvartal'
FORMA = '#soz-filiallar .soz-tahrir'

SAVOLLAR = [
    {'matn': "Chilonzordagi planshetda sotuvchi zakaz oldi. Zakaz qaysi filialga yoziladi?",
     'variantlar': [
         ('sotuvchi', "Sotuvchi har safar o'zi tanlaydi", False,
          "Tanlamaydi: zakaz qurilmaga qarab yoziladi — adashib boshqa filialga yozib qo'yish xavfi yo'q."),
         ('qurilma', "Planshet qaysi filialga biriktirilgan bo'lsa — o'shanga", True,
          "To'g'ri: planshetni filialga Sozlama → «Qurilmalar va parol» → «Filial» bilan bir marta biriktirasiz."),
         ('asosiy', "Har doim asosiy salonga", False, "Yo'q: zakaz planshet biriktirilgan filialga yoziladi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Chilonzorda ikkinchi do'kon ochdingiz. Uni filial qilib qo'shing: nomi — {NOMI}, manzili — {MANZIL}. "
            "U yerda o'z kassasi bo'ladi: «Har filialda alohida kassa» ni yoqing.")


def tekshir(m, javob=None):
    f = Filial.objects.filter(salon=m.salon, faol=True).first()
    return [
        mezon(f, f"Filial qo'shildi: {f.nomi if f else ''}.", "Filial hali qo'shilmagan."),
        mezon(sozlama(m.salon).filial_kassasi, "Har filialda alohida kassa yoqildi — har filial o'z smenasini ochadi.",
              "«Har filialda alohida kassa» hali o'chiq. Uni yoqib, pastdagi «Saqlash» ni bosing."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Filiallar» bo'limiga kiring.",
            f"«Filial qo'shish» ni bosing, nomi — {NOMI}, manzili — {MANZIL}. «Qo'shish» ni bosing.",
            "Pastda chiqqan «Har filialda alohida kassa» ni yoqing va «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Filiallar'),
            {'matn': "«Filial qo'shish» ni bosing.", 'amal': 'bos', 'nishon': {'css': '#soz-filiallar button', 'matn': "Filial qo'shish"},
             'tayyor': {'css': f'{FORMA} input'}},
            {'matn': f"Filial nomini yozing: {NOMI}.", 'amal': 'yoz', 'nishon': {'css': f'{FORMA} input', 'placeholder': 'Chilonzor'},
             'kutilgan': 'uzunlik:4'},
            {'matn': f"Manzilini yozing: {MANZIL}. U shartnoma va hisobotlarda chiqadi.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} label:nth-of-type(2) input'}, 'kutilgan': 'uzunlik:5'},
            {'matn': "«Qo'shish» ni bosing.", 'amal': 'bos', 'nishon': {'css': f'{FORMA} button', 'matn': "Qo'shish"},
             'tayyor': {**SAQLANDI, 'ichida': "Filial qo'shildi"}},
            {'matn': "Filial paydo bo'ldi va pastda yangi tanlov chiqdi. «Har filialda alohida kassa» ni yoqing.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': 'Har filialda alohida kassa'}, 'tayyor': {'css': '.sozlama-saqlash'}},
            SAQLASH]


def bilim(h):
    return [
        "Zakaz qaysi filialga yozilishini sotuvchi tanlamaydi: planshet qaysi filialga biriktirilgan bo'lsa — o'shanga. "
        "Biriktirish bir marta qilinadi: Sozlama → «Qurilmalar va parol» → «Filial».",
    ]


DARS = Dars(
    kod='R4C', nomi='Filiallar', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Filiallar',
    vaziyat="Salon kengaydi — ikkinchi do'kon ochildi. Endi har zakaz, har libos va har so'm qaysi do'konniki ekanini bilish kerak. "
            "Buning uchun filial bir marta qo'shiladi, qolganini tizim o'zi ajratadi.",
    natija="Filial qo'shasiz, unga alohida kassa ochasiz va zakaz qaysi filialga yozilishini bilasiz.",
    xulosa="Filial qo'shildi va har filialning o'z kassasi bor: smena har birida alohida ochiladi va yopiladi. Endi ikki ish qoladi: "
           "filialdagi planshetni Sozlama → «Qurilmalar va parol» → «Filial» bilan unga biriktirish va liboslarni filiallarga "
           "taqsimlash (libos kartasidagi «Filial»). Hisobotlar va Dashboard filial bo'yicha ham ko'rsatadi. Filiallar soni "
           "tarifga bog'liq.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Filiallar «Salon va xodimlar» guruhida. Alohida kassa tanlovi filial qo'shilgandan keyin chiqadi.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
