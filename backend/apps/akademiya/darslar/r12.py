"""R12 — Hisobotlar (rahbar). «Oylik foyda» (Hisobotlar.jsx Pnl, finance/reports.foyda): kassa usuli — pul kirgan kuni
tushum; kirdi − chiqdi = sof foyda; garov hisobga kirmaydi. Urug'da bitta yopilgan zakaz (ijara 300 000, garov olinib
qaytarilgan) va bitta tasdiqlangan xarajat (40 000) — o'quvchi raqamlarni ekrandan o'qiydi."""
from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.finance.models import Xarajat
from apps.finance.services import xarajat_kiritish
from apps.orders.rental import libos_berish, libos_qaytarish
from apps.orders.services import zakaz_yaratish

from .asos import (AVANS, GAROV, IJARA, MIJOZ_FIO, MIJOZ_TELEFON, Dars, faqat_rahbar, katalog, nav, savollarni_tekshir, som,
                   tab)

XARAJAT = 40_000
FOYDA = IJARA - XARAJAT

SAVOLLAR = [
    {'matn': "Bu oy mijozlardan ijara uchun qancha pul kirdi?",
     'variantlar': [
         ('foyda', som(FOYDA), False, f"{som(FOYDA)} — bu sof foyda (xarajat ayirilgandan keyin). Kirgan pul — {som(IJARA)}."),
         ('ijara', som(IJARA), True, f"To'g'ri: «Kirdi» — {som(IJARA)}: avans va qoldiq."),
         ('garov', som(IJARA + GAROV), False,
          f"Garov {som(GAROV)} bu yerga qo'shilmaydi — u mijozning puli edi va qaytarildi. Kirgan pul — {som(IJARA)}."),
     ]},
    {'matn': "Sof foyda qancha va u qanday hisoblandi?",
     'variantlar': [
         ('hammasi', f"{som(IJARA)} — kirgan pulning hammasi", False,
          f"Kirgan pul hali foyda emas: undan xarajat ayiriladi. {som(IJARA)} − {som(XARAJAT)} = {som(FOYDA)}."),
         ('ayirma', f"{som(FOYDA)}: kirgan {som(IJARA)} − chiqqan {som(XARAJAT)}", True,
          "To'g'ri: kirdi − chiqdi. Chiqqan pul — tasdiqlangan xarajatlar, mijozga qaytarilgan pul va sotuvchi bonusi."),
         ('qoshma', f"{som(IJARA + XARAJAT)}: kirgan pul + xarajat", False, "Xarajat qo'shilmaydi, ayiriladi: kirdi − chiqdi."),
     ]},
    {'matn': f"Shu oyda mijoz {som(GAROV)} garov bergan va qaytarib olgan. Nega bu pul hisobotda ko'rinmaydi?",
     'variantlar': [
         ('xato', "Tizim xatosi — garov tushumga kirishi kerak edi", False,
          "Xato emas: garov salonning daromadi emas. U faqat kassa (smena) hisobotida ko'rinadi — keldi va qaytib ketdi."),
         ('mijoz', "Garov — mijozning puli: daromad ham, xarajat ham emas", True,
          "To'g'ri: sahifaning o'zida ham yozilgan — «Garov hisobga kirmaydi». Faqat undan ushlangan jarima daromad bo'ladi."),
         ('keyin', "Garov keyingi oyning hisobotida chiqadi", False, "Hech qaysi oyda chiqmaydi: garov foyda hisobiga umuman kirmaydi."),
     ]},
    {'matn': "Bugun mijoz keyingi oydagi to'yi uchun avans berdi. Bu pul qaysi oyning tushumiga kiradi?",
     'variantlar': [
         ('shu', "Shu oyning — pul kirgan kuni", True,
          "To'g'ri: hisob kassa usulida — pul qaysi kuni kirgan bo'lsa, o'sha kunning tushumi. Shuning uchun hisobot kassadagi pul bilan mos keladi."),
         ('toy', "Keyingi oyning — to'y o'sha oyda", False,
          "Yo'q: tizim to'y sanasiga emas, pul kirgan kuniga qaraydi. Avans bugun kirdi — shu oyning tushumi."),
         ('yopilganda', "Zakaz yopilgan oyning", False, "Zakaz yopilishini kutmaydi: pul kirgan kuni hisobga olinadi."),
     ]},
]


def urug(m):
    l = katalog(m)
    bugun = timezone.localdate()
    smena_ochish(salon=m.salon, xodim=m.xodim, boshlangich_qoldiq=0)
    z = zakaz_yaratish(salon=m.salon, xodim=m.hamkasb, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=bugun,
                       qaytarish=bugun, libos_idlari=[l['togri'].id])
    tolov_qabul(salon=m.salon, xodim=m.xodim, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z)
    tolov_qabul(salon=m.salon, xodim=m.xodim, tur=Tolov.Tur.QOLDIQ, summa=IJARA - AVANS, zakaz=z)
    libos_berish(salon=m.salon, xodim=m.xodim, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': GAROV}])
    libos_qaytarish(salon=m.salon, xodim=m.xodim, zakaz=z)
    xarajat_kiritish(salon=m.salon, xodim=m.xodim, modda=Xarajat.Modda.TOZALASH, summa=XARAJAT, izoh='Zarbof ximchistkaga berildi',
                     kassadan=True)
    return {}


def topshiriq(h):
    return ("Oy tugayapti. «Hisobotlar» → «Oylik foyda» ni oching va «Qayerdan keldi, qayerga ketdi» jadvaliga qarab, "
            "to'rtta savolga javob bering.")


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Hisobotlar» ni oching va «Oylik foyda» bo'limiga o'ting.",
            "«Kirdi» — mijozlardan kirgan pul; «Chiqdi» — xarajatlar va qaytarilgan pul; pastda — «Sof foyda».",
            "Jadval ostidagi izohni o'qing: garov hisobga kirmaydi."]


def yol(h):
    return [nav('Hisobotlar'), tab('Oylik foyda'),
            {'matn': "Bu — oyning asosiy jadvali: «Kirdi», «Chiqdi» va pastda «Sof foyda». Ostidagi izohni ham o'qing. "
                     "Keyin savollarga javob bering.", 'amal': 'kor',
             'nishon': {'css': 'section[aria-label="Qayerdan keldi, qayerga ketdi"]'}}]


def bilim(h):
    return [
        "«Kirdi» — mijozlardan ijara uchun kirgan pul: avans va qoldiq. «Chiqdi» — tasdiqlangan xarajatlar, mijozga qaytarilgan pul "
        "va sotuvchi bonusi. Sof foyda = kirdi − chiqdi.",
        "Garov hisobotga kirmaydi: u mijozning puli — daromad ham, xarajat ham emas. Faqat undan ushlangan jarima daromad bo'ladi.",
        "Hisob kassa usulida: pul qaysi kuni kirgan bo'lsa, o'sha oyning tushumi — to'y qaysi oyda bo'lishidan qat'i nazar.",
    ]


DARS = Dars(
    kod='R12', nomi='Hisobotlar', yonalish='rahbar', personaj='nodira',
    sahifa='Hisobotlar → Oylik foyda',
    vaziyat="Oy oxirida egasining bitta savoli bor: «Bu oy qancha ishladim?» Javob kassadagi pul emas — unda mijozlarning garovi ham "
            "turadi. Javob — «Oylik foyda» sahifasida, va u uch qatordan iborat: kirdi, chiqdi, qoldi.",
    natija="Oylik foyda hisobotini o'qiysiz: qancha kirdi, qancha chiqdi, sof foyda qancha va nega garov unga kirmaydi.",
    xulosa="Hisobot oddiy: kirgan pul − chiqqan pul = sof foyda. Har bir qatorning nomini bossangiz, uni tashkil qilgan yozuvlar "
           "ochiladi. Raqam to'g'ri chiqishi uchun ikki narsa sizga bog'liq: xarajatlar tasdiqlangan bo'lsin (kutayotgani hisobga "
           "kirmaydi) va liboslarning tannarxi kiritilgan bo'lsin. Qolgan hisobotlar ham shu bo'limda: qaysi libos o'zini oqladi, "
           "xodimlar qanday ishladi, kim qarzdor.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Uchta qatorga qarang: «Kirdi», «Chiqdi», «Sof foyda». Javoblar shu jadvalda.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
