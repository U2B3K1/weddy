"""R10 — Pul topshirish va xarajat tasdig'i (rahbar). Xodim kassadan yozgan xarajat rahbar qarorini kutadi (qo'ng'iroqcha →
«Qaroringiz kerak», BoshEkran.jsx Tasdiqlar → finance.xarajat_qarori); rahbarga topshirilgan naqd — «Sizga topshirilgan pul»
(Kassa.jsx Kutayotgan → cash.services.topshiriqni_qabul). Bu — P5 ning qabul tomoni. Ikkalasi Telegramda ham tugma bilan keladi."""
from apps.cash.models import KassaTopshirish, Tolov
from apps.cash.services import inkassatsiya, smena_ochish, tolov_qabul
from apps.finance.models import Xarajat
from apps.finance.services import xarajat_kiritish
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import sozlama

from .asos import AVANS, MIJOZ_FIO, MIJOZ_TELEFON, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, som, toy_katalogi

XARAJAT, TOPSHIRISH, KAM = 40_000, 200_000, 190_000
IZOH = 'Zarbof ximchistkaga berildi'


def savollar(h):
    ism = h['sotuvchi']
    return [
        {'matn': f"Boshqa kuni {ism} «{som(TOPSHIRISH)} topshirdim» dedi, siz esa sanaganda {som(KAM)} chiqdi. Nima qilasiz?",
         'variantlar': [
             ('bosaman', f"«{som(TOPSHIRISH)} qabul qildim» ni bosaman — keyin gaplashamiz", False,
              f"Bossangiz, {som(TOPSHIRISH)} uchun siz javob berasiz — yetmagan {som(TOPSHIRISH - KAM)} sizning zimmangizga o'tadi."),
             ('boshqa', f"«Boshqa summa» ni bosib, sanaganimni — {som(KAM)} ni kiritaman", True,
              f"To'g'ri: siz faqat sanagan pulingizga javob berasiz. Farq {ism}ning hisobida qoladi va smena yopilishida ko'rinadi."),
             ('kutaman', "Hech narsa bosmayman — o'zi hal bo'lar", False,
              "Tasdiqlanmagan topshirish «kutilmoqda» bo'lib osilib turadi — bu pul uchun kim javob berishi noma'lum qoladi. "
              "Sanaganingizni «Boshqa summa» bilan kiriting."),
         ]},
        {'matn': "Xarajatga cheki yo'q, izohi ham shubhali. «Rad etish» ni bossangiz nima bo'ladi?",
         'variantlar': [
             ('qaytadi', "Pul kassaga o'zi qaytadi", False,
              "Pul kassadan allaqachon chiqib bo'lgan — tizim uni qaytara olmaydi. Summa xarajatni yozgan xodimning kamomadi bo'ladi."),
             ('kamomad', "Summa xarajatni yozgan xodimning kamomadi hisoblanadi va unga xabar boradi", True,
              "To'g'ri: soxta xarajat bilan kassadagi kamni «yopib» bo'lmaydi. Shuning uchun rad etishdan oldin xodimdan so'rab ko'ring."),
             ('ochadi', "Xarajat o'chib ketadi, hech narsa o'zgarmaydi", False,
              "O'chmaydi: rad etilgan xarajat tarixda qoladi va summasi xodimning kamomadi bo'lib yoziladi."),
         ]},
    ]


def urug(m):
    s = sozlama(m.salon)
    if s.kassa_rejimi != 'sotuvchi':  # darsda pulni sotuvchining o'zi oladi
        s.kassa_rejimi = 'sotuvchi'
        s.save(update_fields=['kassa_rejimi'])
    l, dan, gacha = toy_katalogi(m)
    sotuvchi = m.hamkasb
    smena_ochish(salon=m.salon, xodim=sotuvchi, boshlangich_qoldiq=200_000)
    z = zakaz_yaratish(salon=m.salon, xodim=sotuvchi, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan, qaytarish=gacha,
                       libos_idlari=[l['togri'].id])
    tolov_qabul(salon=m.salon, xodim=sotuvchi, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z)
    x = xarajat_kiritish(salon=m.salon, xodim=sotuvchi, modda=Xarajat.Modda.TOZALASH, summa=XARAJAT, izoh=IZOH)
    t = inkassatsiya(salon=m.salon, xodim=sotuvchi, rahbar=m.xodim, summa=TOPSHIRISH, izoh='Kunduzgi naqd')
    return {'xarajat': x.id, 'topshirish': t.id, 'sotuvchi': sotuvchi.ism}


def topshiriq(h):
    return (f"{h['sotuvchi']}dan ikki narsa qaroringizni kutyapti. 1) U kassadan {som(XARAJAT)} xarajat yozgan: «{IZOH}» — cheki bor, "
            f"tasdiqlang. 2) U sizga {som(TOPSHIRISH)} naqd topshirdi — sanadingiz, to'g'ri chiqdi: qabul qiling.")


def tekshir(m, javob=None):
    h = m.holat
    x = Xarajat.objects.filter(salon=m.salon, id=h['xarajat']).first()
    t = KassaTopshirish.objects.filter(salon=m.salon, id=h['topshirish']).first()
    return [
        mezon(x and x.holat == Xarajat.Holat.TASDIQLANDI, f"Xarajat tasdiqlandi: {som(XARAJAT)} oylik hisobotga kiradi.",
              "Xarajat rad etilgan — cheki bor edi, tasdiqlash kerak edi. «Qayta boshlash» ni bosing."
              if x and x.holat == Xarajat.Holat.RAD else "Xarajat hali tasdiqlanmagan."),
        mezon(t and t.holat == KassaTopshirish.Holat.QABUL and t.qabul_summa == TOPSHIRISH,
              f"{som(TOPSHIRISH)} qabul qilindi — endi bu pulga siz javob berasiz.",
              f"Boshqa summa qabul qilingan — pul to'g'ri sanalgan edi: {som(TOPSHIRISH)}. «Qayta boshlash» ni bosing."
              if t and t.holat == KassaTopshirish.Holat.QABUL else "Topshirilgan pul hali qabul qilinmagan."),
    ] + savollarni_tekshir(savollar(h), javob)


def qadamlar(h):
    return ["Yuqori paneldagi qo'ng'iroqchani (🔔) bosing: «Qaroringiz kerak» ro'yxatida xarajat turibdi.",
            "Xarajat qatoridagi «Tasdiqlash» ni bosing.",
            "Menyuda «Kassa» ni oching: tepada «Sizga topshirilgan pul» chiqadi.",
            f"«{som(TOPSHIRISH)} qabul qildim» ni bosing."]


def yol(h):
    return [{'matn': "Qo'ng'iroqchada son turibdi — sizni qaror kutyapti. Uni bosing.", 'amal': 'bos',
             'nishon': {'css': 'button.ustki-tugma', 'label': 'Bildirishnomalar'}, 'tayyor': {'css': '.xabar-qarorlar .tasdiq-qator'}},
            {'matn': f"«Qaroringiz kerak»: {h['sotuvchi']} kassadan {som(XARAJAT)} xarajat yozgan — moddasi va izohi shu yerda. "
                     "Cheki bor — «Tasdiqlash» ni bosing.", 'amal': 'bos',
             'nishon': {'css': '.xabar-qarorlar .tasdiq-qator', 'ichida': 'Xarajat'}, 'ichki': {'css': 'button', 'matn': 'Tasdiqlash'}},
            nav('Kassa', "Endi pul. Menyudan «Kassa» ni oching."),
            {'matn': f"«Sizga topshirilgan pul»: {h['sotuvchi']} · {som(TOPSHIRISH)}. Pulni sanadingiz — to'g'ri. "
                     f"«{som(TOPSHIRISH)} qabul qildim» ni bosing.", 'amal': 'bos',
             'nishon': {'css': '.tasdiq-qator', 'ichida': 'inkassatsiya'}, 'ichki': {'css': 'button:not(.ikkinchi)'},
             'tayyor': {'css': '.pos-xabar', 'ichida': 'Qabul qilindi'}}]


def bilim(h):
    return [
        "Pul sanaganingizdan boshqacha chiqsa — «Boshqa summa» ni bosib, o'zingiz sanagan summani kiritasiz. Siz faqat sanagan "
        "pulingizga javob berasiz; farq topshirgan xodimning hisobida qoladi.",
        "Xarajatni «Rad etish» ham mumkin. Unda summa xarajatni yozgan xodimning kamomadi hisoblanadi va unga xabar boradi — "
        "shuning uchun avval xodimning o'zidan so'rab ko'ring.",
    ]


DARS = Dars(
    kod='R10', nomi="Pul topshirish va xarajat tasdig'i", yonalish='rahbar', personaj='nodira',
    sahifa="Qo'ng'iroqcha → Qaroringiz kerak · Kassa",
    vaziyat="Kassadan pul ikki yo'l bilan chiqadi: xarajatga yoki sizning qo'lingizga. Ikkalasida ham oxirgi so'z sizniki: "
            "xarajatni tasdiqlaysiz, pulni sanab qabul qilasiz. Siz bosmaguningizcha tizim bularni «tugallanmagan» deb turadi.",
    natija="Xodim yozgan xarajatni ko'rib chiqasiz va sizga topshirilgan pulni sanab qabul qilasiz.",
    xulosa="Ikkalasi ham yopildi: xarajat oylik hisobotga kirdi, pul esa sotuvchining hisobidan chiqib, sizning zimmangizga o'tdi. "
           "Bularni salonga kelmasdan ham qilsa bo'ladi: Telegram botda aynan shu so'rovlar «Tasdiqlash / Rad etish» va "
           "«Qabul qildim» tugmalari bilan keladi. Qoida bitta: sanamagan pulni qabul qilmang, chekini ko'rmagan xarajatni tasdiqlamang.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=savollar, mos=faqat_rahbar,
    ishora="Qarorlar qo'ng'iroqchada, sizga topshirilgan pul — «Kassa» sahifasining tepasida.",
    qadamlar=qadamlar, yol=yol, xp=70,
)
