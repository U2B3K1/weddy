"""R1 — Boshlash ro'yxati (rahbar). Yangi salon rahbariga qo'ng'iroqcha menyusida «Salonni sozlash» ro'yxati chiqadi
(UstkiPanel.jsx, tenants.views_admin.BoshlashView): rekvizitlar, xodimlar, kategoriyalar, birinchi liboslar. Darsda birinchi
qadam — rekvizitlar — bajariladi (Sozlama → Rekvizitlar, PATCH /api/salon/); qolganlari keyingi darslarda (R2, R5)."""
from apps.tenants.models import Salon

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, sozlama_qatori

YURIDIK, MANZIL = '«Nodira Lux» MChJ', "Toshkent, Chilonzor 5"
MAYDON = '#soz-rekvizitlar .soz-kv-royxat > label:nth-child({}) input'  # 2 — yuridik nom, 4 — manzil


def urug(m):
    Salon.objects.filter(id=m.salon.id).update(boshlash_yopilgan=False, yuridik_nom='', manzil='')
    return {}


def topshiriq(h):
    return (f"Saloningiz Libosa'ga endi ulandi. Qo'ng'iroqchadagi «Salonni sozlash» ro'yxatidan birinchi qadamni bajaring: "
            f"rekvizitlarni kiriting. Yuridik nom: {YURIDIK}. Manzil: {MANZIL}.")


def tekshir(m, javob=None):
    s = Salon.objects.get(id=m.salon.id)
    return [
        mezon(s.yuridik_nom.strip(), "Yuridik nom kiritildi va saqlandi.", "Yuridik nom hali saqlanmagan. Yozib, pastdagi «Saqlash» ni bosing."),
        mezon(s.manzil.strip(), "Manzil kiritildi — shartnomada chiqadi.", "Manzil hali saqlanmagan. Yozib, pastdagi «Saqlash» ni bosing."),
    ]


def qadamlar(h):
    return ["Yuqori paneldagi qo'ng'iroqchani (🔔) bosing: tepasida «Salonni sozlash» ro'yxati bor.",
            "«Salon rekvizitlarini kiriting» qadamini bosing — Sozlama ochiladi. «Rekvizitlar» bo'limiga kiring.",
            f"«Yuridik nom» ga {YURIDIK}, «Manzil» ga {MANZIL} deb yozing.",
            "Pastda chiqqan «Saqlash» ni bosing."]


def yol(h):
    return [{'matn': "Yuqori paneldagi qo'ng'iroqchani bosing — tizim sizga nima qilish kerakligini shu yerda aytadi.", 'amal': 'bos',
             'nishon': {'css': 'button.ustki-tugma', 'label': 'Bildirishnomalar'}, 'tayyor': {'css': '.xabar-sozlash'}},
            {'matn': "«Salonni sozlash»: to'rt qadamdan bittasi bajarilgan. Birinchisini bosing: «Salon rekvizitlarini kiriting».",
             'amal': 'bos', 'nishon': {'css': 'button.xabar-qadam', 'ichida': 'rekvizit'}},
            sozlama_qatori('Rekvizitlar'),
            {'matn': f"«Yuridik nom» ga yozing: {YURIDIK}.", 'amal': 'yoz', 'nishon': {'css': MAYDON.format(2)}, 'kutilgan': 'uzunlik:5'},
            {'matn': f"«Manzil» ga yozing: {MANZIL}.", 'amal': 'yoz', 'nishon': {'css': MAYDON.format(4)}, 'kutilgan': 'uzunlik:5'},
            SAQLASH]


DARS = Dars(
    kod='R1', nomi="Boshlash ro'yxati", yonalish='rahbar', personaj='nodira',
    sahifa="Qo'ng'iroqcha → Salonni sozlash → Sozlama",
    vaziyat="Yangi salonda birinchi zakazgacha to'rtta ish bor. Ularni eslab yurish shart emas — tizim qo'ng'iroqchada ro'yxat "
            "qilib beradi va har birini bosganingizda kerakli joyga olib boradi.",
    natija="Yangi salonni ishga tushirish uchun nima qilish kerakligini bilasiz va birinchi qadamni bajarasiz.",
    xulosa="Rekvizitlar saqlandi: endi ular har bir shartnoma va kvitansiyada chiqadi. Ro'yxatda yana uchta qadam bor: sotuvchilarni "
           "qo'shish va PIN berish, kategoriyalarni tekshirish, birinchi liboslarni rasmi va tannarxi bilan qo'shish. Hammasi "
           "bajarilgach ro'yxat o'zi yo'qoladi; oldinroq kerak bo'lmasa — «Yashirish».",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=faqat_rahbar,
    ishora="Ro'yxat qo'ng'iroqcha menyusining eng tepasida. Rekvizitlar — Sozlamaning «Salon va xodimlar» guruhida.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
