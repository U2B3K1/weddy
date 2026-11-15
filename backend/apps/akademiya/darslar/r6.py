"""R6 — Bron va tozalash qoidalari (rahbar). Tozalash buferi: qaytgan libos keyingi mijozgacha necha kun band turadi.
Sozlama tugma orqali emas, oqibati orqali o'rgatiladi."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, sozlama_qatori, toy_katalogi

KERAK = 2
BUFER = {'css': '.soz-qiymat-k', 'ichida': 'Tozalash buferi'}


def urug(m):
    toy_katalogi(m)
    return {}


def topshiriq(h):
    return (f"Kimyoviy tozalash liboslarni {KERAK} kunda qaytaryapti, tizimda esa 1 kun turibdi — tozalashdan chiqmagan libos "
            f"yangi mijozga bron bo'lib qolyapti. Tozalash buferini {KERAK} kunga o'zgartiring.")


def tekshir(m, javob=None):
    kun = sozlama(m.salon).bufer_kun
    return [mezon(kun == KERAK, f"Tozalash buferi {KERAK} kun qilib saqlandi.",
                  f"Tozalash buferi hozir {kun} kun. {KERAK} kun qilib, pastdagi «Saqlash» ni bosing.")]


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Bron va garov» bo'limiga kiring.",
            f"«Tozalash buferi» yonidagi «+» ni bosib, {KERAK} kun qiling.",
            "Pastda chiqqan «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Bron va garov'),
            {'matn': f"«Tozalash buferi» ni {KERAK} kun qiling: «+» ni bosing.", 'amal': 'bos', 'nishon': BUFER,
             'tayyor': {'css': 'input', 'label': 'Tozalash buferi, kun', 'qiymat': str(KERAK)}},
            SAQLASH]


DARS = Dars(
    kod='R6', nomi='Bron va tozalash qoidalari', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Bron va garov',
    vaziyat="Shanba kuni libos qaytdi, yakshanbaga esa boshqa mijozga bron qilingan ekan — libos hali tozalashda. "
            "Bunday holat sozlamadagi bitta raqamga bog'liq.",
    natija="Bron qoidalarini o'zgartira olasiz va har biri bandlikka qanday ta'sir qilishini bilasiz.",
    xulosa=f"Endi har bir libos qaytgandan keyin {KERAK} kun band turadi — sotuvchilar bu kunlarga uni bron qila olmaydi. "
           "Shu bo'limdagi qolgan ikki raqam: «Avanssiz bron» — avans to'lanmagan bron necha soatdan keyin o'zi bekor bo'lishi; "
           "«Libosni qulflash» — sotuvchi tanlagan libos boshqa sotuvchidan necha daqiqa yashirilishi. "
           "Qoida yangi zakazlarga ta'sir qiladi; mavjud bronlar o'zgarmaydi.",
    tekshirilgan='2026-11-13 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=faqat_rahbar,
    ishora="Liboslarning band turishi «Sozlama → Bron va garov» da belgilanadi.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
