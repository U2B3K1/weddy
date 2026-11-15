"""R7C — Mavsumiy ustama (rahbar). Sozlama → «Mavsumiy narx» (MavsumiyNarx.jsx): almashtirgich (`mavsumiy_narx`) va qoidalar
(orders.MavsumiyNarx). Ustama zakaz yaratilganda olib ketish kuniga qarab qo'shiladi; bir kunga bir nechta qoida to'g'ri kelsa,
eng kattasi olinadi (orders/pricing.mavsumiy_qoida); sana ko'chirilsa qayta hisoblanadi (changes.sanani_kochirish)."""
from apps.orders.models import MavsumiyNarx
from apps.tenants.models import sozlama

from .asos import IJARA, SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, som, sozlama_qatori

NOMI, FOIZ = 'Dam olish kunlari', 10
SHANBA, YAKSHANBA = 5, 6
QOSH = '#soz-mavsumiy details.soz-qosh-details'

SAVOLLAR = [
    {'matn': f"Libosning ijarasi {som(IJARA)}. Mijoz uni shanba kuni olib ketadi. Zakazda jami qancha chiqadi?",
     'variantlar': [
         ('asl', som(IJARA), False, f"Shanba — qoida kuni: {FOIZ}% ustama o'zi qo'shiladi. {som(IJARA)} + {som(IJARA * FOIZ // 100)}."),
         ('ustama', som(IJARA + IJARA * FOIZ // 100), True,
          f"To'g'ri: {som(IJARA)} + {FOIZ}% = {som(IJARA + IJARA * FOIZ // 100)}. Sotuvchi hech narsa qo'shmaydi — tizim o'zi."),
     ]},
    {'matn': "Boshqa mijoz libosni juma kuni olib ketib, dushanba qaytaradi — shanba va yakshanba ham uning qo'lida. Ustama bormi?",
     'variantlar': [
         ('bor', "Bor — dam olish kunlari ham ijarada", False,
          "Yo'q: ustama olib ketish kuniga qarab qo'shiladi. Juma — qoida kuni emas."),
         ('yoq', "Yo'q — ustama olib ketish kuniga qarab qo'shiladi", True,
          "To'g'ri: tizim olib ketish kunini qoidaga solishtiradi. Sana ko'chirilsa, ustama yangi kunga qarab qayta hisoblanadi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Shanba va yakshanba — to'y kunlari, libos ham shu kunlarda ko'p so'raladi. Shu kunlarda olib ketiladigan "
            f"liboslarga {FOIZ}% ustama qo'ying: mavsumiy narxni yoqing va «{NOMI}» qoidasini qo'shing.")


def tekshir(m, javob=None):
    q = MavsumiyNarx.objects.filter(salon=m.salon, faol=True).first()
    kunlar = sorted(q.hafta_kunlari or []) if q else []
    return [
        mezon(sozlama(m.salon).mavsumiy_narx, "Mavsumiy narx yoqildi.",
              "Mavsumiy narx o'chiq — qoida bo'lsa ham narxga qo'shilmaydi. Almashtirgichni yoqib, «Saqlash» ni bosing."),
        mezon(q and q.foiz == FOIZ, f"Qoida qo'shildi: {FOIZ}% ustama.",
              "Qoida hali qo'shilmagan." if not q else f"Ustama {q.foiz:g}% — {FOIZ}% bo'lishi kerak."),
        mezon(kunlar == [SHANBA, YAKSHANBA], "Faqat shanba va yakshanbada ishlaydi.",
              "Qoida shanba va yakshanbaga qo'yilishi kerak — hafta kunlaridan «Sh» va «Ya» ni belgilang."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Mavsumiy narx» bo'limiga kiring.",
            "Sarlavha yonidagi almashtirgichni yoqing va pastdagi «Saqlash» ni bosing.",
            f"«Qoida qo'shish» ni oching: nomi — {NOMI}, ustama — {FOIZ}, hafta kunlaridan «Sh» va «Ya».",
            "«Qo'shish» ni bosing."]


def kun(nom, matn):
    return {'matn': matn, 'amal': 'bos', 'nishon': {'css': f'{QOSH} .kunlar label', 'matn': nom}}


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Mavsumiy narx'),
            {'matn': "Mavsumiy narx o'chiq. Sarlavha yonidagi almashtirgichni yoqing.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': 'Mavsumiy narx yoqilgan'}, 'tayyor': {'css': '.sozlama-saqlash'}},
            {**SAQLASH, 'matn': "Avval shu o'zgarishni saqlang: pastdagi «Saqlash» ni bosing."},
            {'matn': "Endi qoida. «Qoida qo'shish» ni oching.", 'amal': 'bos', 'nishon': {'css': f'{QOSH} > summary'},
             'tayyor': {'css': f'{QOSH}[open] input'}},
            {'matn': f"Qoida nomini yozing: {NOMI}.", 'amal': 'yoz', 'nishon': {'css': f'{QOSH} input', 'placeholder': "To'y mavsumi"},
             'kutilgan': 'uzunlik:5'},
            {'matn': f"Ustamani yozing: {FOIZ} (foizda).", 'amal': 'yoz', 'nishon': {'css': f'{QOSH} input[type=number]'},
             'kutilgan': f'raqam:{FOIZ}'},
            kun('Sh', "Sanalarni bo'sh qoldiring — qoida butun yil ishlaydi. Hafta kunlaridan «Sh» (shanba) ni belgilang."),
            kun('Ya', "«Ya» (yakshanba) ni ham belgilang."),
            {'matn': "«Qo'shish» ni bosing.", 'amal': 'bos', 'nishon': {'css': f'{QOSH} button', 'matn': "Qo'shish"},
             'tayyor': {'css': '#soz-mavsumiy .soz-izoh', 'ichida': "Qoida qo'shildi"}}]


def bilim(h):
    return [
        "Ustama narxga foiz bo'lib qo'shiladi: masalan 200 000 so'mlik libos 10% ustama bilan 220 000 so'm. Sotuvchi hech narsa "
        "qo'shmaydi — tizim o'zi.",
        "Tizim faqat olib ketish kuniga qaraydi. Libos qoidaga tushmaydigan kuni olib ketilsa, keyingi kunlarda mijoz qo'lida "
        "tursa ham ustama yo'q.",
    ]


DARS = Dars(
    kod='R7C', nomi='Mavsumiy ustama', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Mavsumiy narx',
    vaziyat="To'y mavsumida va dam olish kunlarida libos talabi oshadi. Narxni har safar qo'lda ko'tarmang: qoidani bir marta "
            "yozasiz, tizim kerakli kunlarda ustamani o'zi qo'shadi.",
    natija="Mavsumiy ustama qoidasini qo'shasiz va u qachon qo'llanishini bilasiz.",
    xulosa=f"Endi shanba va yakshanba kuni olib ketiladigan har bir zakazga {FOIZ}% ustama o'zi qo'shiladi va zakaz kartasida "
           "alohida qator bo'lib ko'rinadi. To'y mavsumi uchun sanalar oralig'i bilan yana bir qoida qo'shish mumkin — bir kunga "
           "ikkita qoida to'g'ri kelsa, kattasi olinadi. Qoidani vaqtincha to'xtatish uchun uni o'chirib qo'yish yetarli.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Ikki narsa kerak: mavsumiy narx yoqilgan bo'lsin va kamida bitta qoida bo'lsin.",
    qadamlar=qadamlar, yol=yol, xp=70,
)
