"""R12B — Kunlik hisobot va Dashboard (rahbar). Sozlama → «Dashboard va hisobot» (Sozlamalar.jsx `dashbord`):
`kunlik_hisobot` / `kunlik_hisobot_vaqti` — rahbarga Telegramda kun yakuni (notify/management/commands/kunlik_hisobot.py;
o'quv salonlari chetlab o'tiladi); `qoplamagan_royxat` / `qoplamagan_kun` — uzoq berilmagan va o'zini qoplamagan liboslar
Dashboardda. Botdagi «📊 Bugun» shu hisobotni istalgan payt chiqaradi (bot_menyu._bugun)."""
import datetime

from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

VAQT, KUN = datetime.time(20, 0), 90

SAVOLLAR = [
    {'matn': "Kunlik hisobot qayerga keladi?",
     'variantlar': [
         ('sms', "SMS bo'lib telefonga", False, "SMS emas: hisobot Telegram botga keladi — Telegramingiz ilovada ulangan bo'lishi kerak."),
         ('tg', "Telegram botga — Telegramim ilovada ulangan bo'lsa", True,
          "To'g'ri: kassa, zakazlar va qarzlar bir xabarda. Kunning istalgan paytida ham botdagi «📊 Bugun» shu hisobotni chiqaradi."),
         ('ilova', "Faqat ilovada, Dashboardda", False,
          "Dashboard — ilovada. Kunlik hisobot esa belgilangan vaqtda Telegram botga keladi."),
     ]},
    {'matn': f"Bir libos {KUN} kundan beri hech kimga berilmagan va hali o'zini qoplamagan. Uni qayerda ko'rasiz?",
     'variantlar': [
         ('dash', "Dashboard'da — uzoq bo'sh turgan liboslar ro'yxatida", True,
          "To'g'ri: bunday liboslar Dashboard'da chiqadi — narxini tushirish, reklama qilish yoki sotish haqida o'ylash vaqti."),
         ('sanoq', "Sanoq natijasida", False, "Sanoq libos joyidami-yo'qmi ko'rsatadi. Uzoq berilmaganlari — Dashboard'da."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Salon soat 20:00 da yopiladi — kunlik hisobot shu vaqtda kelsin. Dashboard'dagi «uzoq bo'sh turgan liboslar» "
            f"ro'yxati esa {KUN} kundan beri berilmagan liboslarni ko'rsatsin.")


def tekshir(m, javob=None):
    s = sozlama(m.salon)
    return [
        mezon(s.kunlik_hisobot and s.kunlik_hisobot_vaqti == VAQT, "Kunlik hisobot soat 20:00 da keladi.",
              f"Hisobot vaqti hozir {s.kunlik_hisobot_vaqti:%H:%M} — 20:00 qilib, «Saqlash» ni bosing."),
        mezon(s.qoplamagan_royxat and s.qoplamagan_kun == KUN, f"Uzoq bo'sh turgan liboslar — {KUN} kundan.",
              f"Hozir {s.qoplamagan_kun} kun — {KUN} qilib, «Saqlash» ni bosing."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Dashboard va hisobot» bo'limiga kiring.",
            "«Yuborish vaqti» ni 20:00 qiling.",
            f"«Necha kundan keyin ro'yxatga tushadi» ni {KUN} qiling va «Saqlash» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Dashboard va hisobot'),
            {'matn': "Kunlik hisobot yoqilgan, soat 21:00 da keladi. «Yuborish vaqti» ni 20:00 qiling.", 'amal': 'yoz',
             'nishon': {'css': 'input', 'label': 'Kunlik hisobot yuborish vaqti'}, 'kutilgan': 'raqam:2000'},
            {'matn': f"«Necha kundan keyin ro'yxatga tushadi» ga yozing: {KUN}.", 'amal': 'yoz',
             'nishon': {'css': 'input', 'label': "Bo'sh turgan kun"}, 'kutilgan': f'raqam:{KUN}'},
            SAQLASH]


def bilim(h):
    return [
        "Kunlik hisobot Telegram botga keladi — buning uchun Telegramingiz ilovada ulangan bo'lishi kerak. Kunning istalgan paytida "
        "botdagi «📊 Bugun» ham shu hisobotni chiqaradi.",
        "Siz belgilagan kundan beri hech kimga berilmagan va hali o'zini qoplamagan liboslar Dashboard'da — uzoq bo'sh turgan "
        "liboslar ro'yxatida chiqadi.",
    ]


DARS = Dars(
    kod='R12B', nomi='Kunlik hisobot va Dashboard', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Dashboard va hisobot',
    vaziyat="Kun tugadi — salonga borib kassani tekshirish shart emas. Hisobot o'zi keladi: qancha kirdi, nechta zakaz, kim "
            "qarzdor. Faqat qachon kelishini va nimani ko'rishni xohlashingizni aytib qo'yasiz.",
    natija="Kunlik hisobot vaqtini va Dashboard'dagi ogohlantirishni o'zingizga moslaysiz.",
    xulosa="Hisobot har kuni soat 20:00 da Telegram botga keladi. U kelishi uchun Telegramingiz ilovada ulangan bo'lishi kerak "
           f"(qo'ng'iroqcha menyusi). Dashboard'da esa {KUN} kundan beri berilmagan va o'zini qoplamagan liboslar ro'yxati chiqadi. "
           "Hisobot kerak bo'lmasa — o'chirib qo'yasiz, «📊 Bugun» baribir istalgan payt ishlaydi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="«Dashboard va hisobot» — «Ko'rinish va xabarlar» guruhida.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
