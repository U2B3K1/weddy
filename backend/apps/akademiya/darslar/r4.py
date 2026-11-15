"""R4 — Kassa tartibi (rahbar). Kim pul qabul qiladi: sotuvchining o'zi yoki alohida kassir.
Bu sozlama butun salon ishini o'zgartiradi — dars uni oqibati bilan ko'rsatadi."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, sozlama_qatori, toy_katalogi


def urug(m):
    toy_katalogi(m)
    s = sozlama(m.salon)
    s.kassa_rejimi = 'sotuvchi'  # dars «sotuvchi o'zi kassir» holatidan boshlanadi
    s.save(update_fields=['kassa_rejimi'])
    return {}


def topshiriq(h):
    return ("Saloningizga alohida kassir oldingiz. Bundan buyon sotuvchilar faqat zakaz oladi, pulni esa kassir qabul qiladi. "
            "Kassa tartibini shunga o'zgartiring.")


def tekshir(m, javob=None):
    rejim = sozlama(m.salon).kassa_rejimi
    return [mezon(rejim == 'kassir', "Kassa tartibi «Alohida kassir» ga o'tdi va saqlandi.",
                  "Kassa tartibi o'zgarmagan. «Alohida kassir» ni tanlagach, pastdagi «Saqlash» ni bosish kerak — "
                  "saqlanmaguncha hech narsa o'zgarmaydi.")]


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Kassa» bo'limiga kiring.",
            "«Alohida kassir» kartasini tanlang.",
            "Pastda chiqqan «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Kassa'),
            {'matn': "Ikki tartibni o'qing va «Alohida kassir» ni tanlang.", 'amal': 'bos',
             'nishon': {'css': 'label.soz-radio', 'ichida': 'Alohida kassir'}, 'tayyor': {'css': '.sozlama-saqlash'}},
            SAQLASH]


DARS = Dars(
    kod='R4', nomi='Kassa tartibi', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Kassa',
    vaziyat="Salonda pul kimning qo'lidan o'tadi? Bu bitta sozlama, lekin u hamma xodimning ekranini o'zgartiradi. "
            "Uni tanlashdan oldin oqibatini bilish kerak.",
    natija="Kassa tartibini almashtira olasiz va bu xodimlar ishida nimani o'zgartirishini bilasiz.",
    xulosa="Endi sotuvchilar pulga tegmaydi: ularning menyusida to'lov yo'q, zakazlari kassirning «To'lov kutayotganlar» "
           "ro'yxatida chiqadi. Ikki narsani eslab qoling: kamida bitta xodimga «Kassir» roli berilishi kerak (bo'lmasa pulni "
           "faqat siz qabul qilasiz), va tartibni almashtirishdan oldin ochiq smena yopilishi shart — tizim aks holda ruxsat bermaydi.",
    tekshirilgan='2026-11-13 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=faqat_rahbar,
    ishora="Sozlamada har o'zgarish «Saqlash» bosilgandan keyingina kuchga kiradi.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
