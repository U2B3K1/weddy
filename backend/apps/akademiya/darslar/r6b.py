"""R6B — Garov turlari (rahbar). Libos berishda qaysi garovlar qabul qilinadi: pul, hujjat, tillo buyum.
O'chirilgan tur zakazda umuman chiqmaydi (rental.py: sozlama.zalog_turlari())."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, sozlama_qatori

TUR = 'Tillo buyum'


def urug(m):
    return {}


def topshiriq(h):
    return (f"Saloningiz tillo buyumni garovga olmaslikka qaror qildi: uni saqlash javobgarligi katta. "
            f"Garov turlaridan «{TUR}» ni olib tashlang — pul va hujjat qolsin.")


def tekshir(m, javob=None):
    s = sozlama(m.salon)
    return [
        mezon(not s.zalog_tillo, f"«{TUR}» garov turlaridan olib tashlandi va saqlandi.",
              f"«{TUR}» hali yoqilgan. Belgisini olib tashlab, pastdagi «Saqlash» ni bosing."),
        mezon(s.zalog_pul and s.zalog_hujjat, "Pul va hujjat garovi joyida.",
              "Pul yoki hujjat garovi ham o'chib qolgan — ularni qayta belgilab, saqlang."),
    ]


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Bron va garov» bo'limiga kiring.",
            f"«Garov turlari» ostidagi «{TUR}» kartasidan belgini olib tashlang.",
            "Pastda chiqqan «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Bron va garov'),
            {'matn': f"«Garov turlari» ostida uchta karta bor. «{TUR}» ni bosib, belgisini olib tashlang.", 'amal': 'bos',
             'nishon': {'css': 'label.soz-belgi', 'ichida': TUR}, 'tayyor': {'css': '.sozlama-saqlash'}},
            SAQLASH]


DARS = Dars(
    kod='R6B', nomi='Garov turlari', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Bron va garov',
    vaziyat="Garov — libos butun qaytishining kafolati. Uni nima bilan olishingizni bir marta shu yerda belgilaysiz — "
            "sotuvchi libos berayotganda faqat siz ruxsat bergan turlarni ko'radi.",
    natija="Salon qabul qiladigan garov turlarini belgilay olasiz.",
    xulosa=f"Endi libos topshirishda sotuvchiga faqat «Pul» va «Hujjat» chiqadi — «{TUR}» ni tanlab bo'lmaydi. "
           "Garov ijara haqi emas: pul garovi libos qaytgach mijozga qaytariladi, hujjat va buyum esa qo'liga beriladi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=faqat_rahbar,
    ishora="Garov turlari «Sozlama → Bron va garov» bo'limining pastki qismida.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
