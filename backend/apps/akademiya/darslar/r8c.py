"""R8C — Shartnoma bandlari (rahbar). Sozlama → «Shartnoma bandlari» (Sozlamalar.jsx `shartnoma`): salonning o'z bandlari
(`shartnoma_bandlari`, 15 tagacha) avtomatik bandlardan keyin chiqadi; ijara muddati, to'lov, garov, jarima va avans qaytarish
bandlari sozlamalardan o'zi yoziladi (orders/hujjatlar.py)."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

SARLAVHA = 'Libosni yuvish'
MATN = "Mijoz libosni o'zi yuvmaydi va dazmollamaydi — buni salon qiladi."
FORMA = '#soz-shartnoma .soz-tahrir'

SAVOLLAR = [
    {'matn': "Kechikish jarimasini kuniga 50 000 so'm qildingiz. Buni shartnomaga alohida band qilib yozish kerakmi?",
     'variantlar': [
         ('ha', "Ha — aks holda shartnomada chiqmaydi", False,
          "Shart emas: ijara muddati, to'lov, garov, jarima va avans qaytarish bandlari sozlamalardan o'zi yoziladi."),
         ('yoq', "Yo'q — jarima, garov va avans qaytarish bandlari sozlamadan o'zi yoziladi", True,
          "To'g'ri: bu yerga faqat salonning o'z qo'shimcha qoidalari yoziladi. Ikki marta yozilsa, ular bir-biriga zid qolishi mumkin."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return ("Bir mijoz libosni uyda yuvib, buzib qo'ydi. Endi bu shartnomada aniq yozilsin. Yangi band qo'shing: "
            f"sarlavha — «{SARLAVHA}», matn — «{MATN}»")


def tekshir(m, javob=None):
    bandlar = [b for b in sozlama(m.salon).shartnoma_bandlari or [] if b.get('sarlavha', '').strip() and b.get('matn', '').strip()]
    return [
        mezon(bandlar, f"Band saqlandi: «{bandlar[0]['sarlavha'] if bandlar else ''}». U har yangi shartnomada chiqadi.",
              "Band hali saqlanmagan: sarlavha va matnni yozib, «Tayyor» va pastdagi «Saqlash» ni bosing."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Shartnoma bandlari» bo'limiga kiring.",
            "«Band qo'shish» ni bosing, sarlavha va matnni yozing.",
            "«Tayyor» ni, keyin pastdagi «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Shartnoma bandlari'),
            {'matn': "«Band qo'shish» ni bosing.", 'amal': 'bos', 'nishon': {'css': '#soz-shartnoma button', 'matn': "Band qo'shish"},
             'tayyor': {'css': f'{FORMA} textarea'}},
            {'matn': f"Sarlavhani yozing: {SARLAVHA}.", 'amal': 'yoz', 'nishon': {'css': f'{FORMA} label:nth-of-type(1) input'},
             'kutilgan': 'uzunlik:5'},
            {'matn': f"Band matnini yozing: {MATN}", 'amal': 'yoz', 'nishon': {'css': f'{FORMA} textarea'}, 'kutilgan': 'uzunlik:10'},
            {'matn': "«Tayyor» ni bosing — band ro'yxatga tushadi.", 'amal': 'bos', 'nishon': {'css': f'{FORMA} button', 'matn': 'Tayyor'}},
            SAQLASH]


def bilim(h):
    return [
        "Jarima, garov va avans qaytarish bandlari shartnomaga sozlamadan o'zi yoziladi. Bu yerga faqat salonning qo'shimcha "
        "qoidalari qo'shiladi — bir narsa ikki marta yozilsa, bandlar bir-biriga zid qolishi mumkin.",
    ]


DARS = Dars(
    kod='R8C', nomi='Shartnoma bandlari', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Shartnoma bandlari',
    vaziyat="Mijoz imzolaydigan shartnoma — tortishuvda sizning himoyangiz. Asosiy bandlarni tizim o'zi yozadi, salonning "
            "o'z qoidalarini esa siz qo'shasiz: ular har bir zakaz shartnomasida chiqadi.",
    natija="Shartnomaga salonning o'z bandini qo'shasiz va qaysi bandlar avtomatik yozilishini bilasiz.",
    xulosa="Band saqlandi: endi u har bir yangi shartnomada, avtomatik bandlardan keyin chiqadi. Shartnomani zakaz kartasidagi "
           "«Chop etish» bilan ko'rib tekshirishingiz mumkin. 15 tagacha band qo'shiladi; keraksizini «Tahrirlash» → «Bandni olib "
           "tashlash» bilan o'chirasiz. Rekvizitlar (salon nomi, manzil) — Sozlama → «Rekvizitlar» da.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Shartnoma bandlari «Zakaz qoidalari» guruhining oxirida. Band avval «Tayyor», keyin «Saqlash» bilan saqlanadi.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
