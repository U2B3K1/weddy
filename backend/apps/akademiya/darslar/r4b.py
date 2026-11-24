"""R4B — Sotuvchi bonusi (rahbar). Sozlama → Salon va xodimlar → «Sotuvchi bonusi» (Sozlamalar.jsx `bonus`):
bonus — libos qaytarib olingan (qaytarish akti shu oyda) zakazlar summasidan foiz, faqat sotuvchi rolidagilarga
(finance/reports._bonuslar); oylik foydadan o'zi ayiriladi (reports.foyda: `sotuvchi_bonusi` chiqim qatori)."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, som, sozlama_qatori

FOIZ = 5
ZAKAZ = 2_000_000

SAVOLLAR = [
    {'matn': f"Madina {som(ZAKAZ)} lik zakaz oldi va avansni shu oy qabul qildi. To'y keyingi oyda, libos o'shanda qaytadi. "
             f"Uning {som(ZAKAZ * FOIZ // 100)} bonusi qaysi oyda hisoblanadi?",
     'variantlar': [
         ('avans', "Shu oy — avans olingan oyda", False,
          "Yo'q: bonus xizmat to'liq ko'rsatilganda — libos qaytarib olinganda hisoblanadi. Bekor bo'lgan zakazga bonus yozilib qolmaydi."),
         ('qaytgan', "Keyingi oy — libos qaytarib olingan oyda", True,
          "To'g'ri: bonus libos qaytarib olingan oyning hisobiga tushadi. Har sotuvchining summasi — Hisobotlar → «Sotuvchi bonusi»."),
         ('yil', "Yil oxirida bir yo'la", False, "Bonus har oy hisoblanadi — libos qaytarib olingan oyda."),
     ]},
    {'matn': "Oy oxirida Madinaga bonusini naqd berdingiz. Buni xarajat qilib yozasizmi?",
     'variantlar': [
         ('ha', "Ha — «Boshqa» moddasi bilan xarajat qilaman", False,
          "Shunda bonus ikki marta ayiriladi: tizim uni oylik foydadan allaqachon o'zi ayirgan."),
         ('yoq', "Yo'q — tizim bonusni oylik foydadan o'zi ayiradi", True,
          "To'g'ri: «Oylik foyda» da «Sotuvchi bonusi» alohida chiqim qatori bo'lib turadi. Qayta yozilsa, foyda kam ko'rinadi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Sotuvchilar ko'proq harakat qilsin deb bonus joriy qilmoqchisiz: har bir yopilgan zakaz summasidan {FOIZ}%. "
            "Sozlamada bonusni yoqing va foizini qo'ying.")


def tekshir(m, javob=None):
    s = sozlama(m.salon)
    return [
        mezon(s.sotuvchi_bonusi, "Sotuvchi bonusi yoqildi va saqlandi.",
              "Bonus hali o'chiq. Almashtirgichni yoqib, pastdagi «Saqlash» ni bosing."),
        mezon(s.bonus_foiz == FOIZ, f"Bonus foizi — {FOIZ}%.", f"Bonus foizi hozir {s.bonus_foiz:g}% — {FOIZ}% bo'lishi kerak."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Sotuvchi bonusi» bo'limiga kiring.",
            "Sarlavha yonidagi almashtirgichni yoqing.",
            f"«Bonus foizi» ga {FOIZ} yozing va pastdagi «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Sotuvchi bonusi'),
            {'matn': "Bonus hozir o'chiq. «Sotuvchi bonusi» sarlavhasi yonidagi almashtirgichni yoqing.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': 'Sotuvchi bonusi yoqilgan'}, 'tayyor': {'css': '.sozlama-saqlash'}},
            {'matn': f"«Bonus foizi» ga yozing: {FOIZ}.", 'amal': 'yoz',
             'nishon': {'css': 'input', 'label': 'Bonus, zakazlar summasidan %'}, 'kutilgan': f'raqam:{FOIZ}'},
            SAQLASH]


def bilim(h):
    return [
        "Bonus zakaz olingan kuni emas, libos qaytarib olingan oyda hisoblanadi. Har sotuvchining summasi — "
        "Hisobotlar → «Sotuvchi bonusi».",
        "Bonusni xarajat qilib yozmaysiz: tizim uni «Oylik foyda» dan o'zi ayiradi. Qayta yozilsa, foyda kam ko'rinadi.",
    ]


DARS = Dars(
    kod='R4B', nomi='Sotuvchi bonusi', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Sotuvchi bonusi',
    vaziyat="Sotuvchi yaxshi ishlasa, buni pulda sezishi kerak. Bonusni qo'lda hisoblab o'tirmang — foizni bir marta qo'ying, "
            "tizim har oy har sotuvchi uchun o'zi hisoblaydi.",
    natija="Sotuvchi bonusini yoqasiz va u qachon, nimadan hisoblanishini bilasiz.",
    xulosa=f"Bonus yoqildi: endi libos qaytarib olingan har bir zakaz summasidan sotuvchiga {FOIZ}% hisoblanadi. Kim qancha "
           "olishini Hisobotlar → «Sotuvchi bonusi» da ko'rasiz, sotuvchi esa o'zinikini botdagi «📊 Bugun» da. Bonus faqat "
           "sotuvchi rolidagi xodimlarga yoziladi va oylik foydadan o'zi ayiriladi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Bonus «Salon va xodimlar» guruhida: avval almashtirgich, keyin foiz.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
