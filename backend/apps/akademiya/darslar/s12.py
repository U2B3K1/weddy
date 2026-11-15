"""S12 — Sanoqda qatnashish (sotuvchi va kassir). Sanoqni rahbar boshlaydi; xodim javondagi buyumni artikul bo'yicha
yoki ro'yxatdan «Topildi» deb belgilaydi (LibosSanogi.jsx OchiqSanoq → catalog/sanoq.py belgilash). Yakunlash — rahbar ishi (R11)."""
from apps.catalog.models import SanoqQatori
from apps.catalog.sanoq import sanoq_boshlash

from .asos import LIBOSLAR, Dars, faqat_xodim, katalog, mezon, nav, tab

A, B = LIBOSLAR['togri'], LIBOSLAR['boshqa_olcham']  # M-003 Zarbof, M-002 Adras


def urug(m):
    l = katalog(m)
    s = sanoq_boshlash(salon=m.salon, xodim=m.hamkasb)
    return {'sanoq': s.id, 'a': l['togri'].id, 'b': l['boshqa_olcham'].id}


def topshiriq(h):
    return (f"Rahbar sanoq boshladi va sizdan yordam so'radi. Javonda ikkita libosni topdingiz: yorlig'ida {A[0]} ({A[1]}) va "
            f"{B[0]} ({B[1]}). Ikkalasini sanoqda «topildi» deb belgilang: birinchisini artikulini terib, ikkinchisini ro'yxatdan.")


def tekshir(m, javob=None):
    h = m.holat
    topilgan = set(SanoqQatori.objects.filter(salon=m.salon, sanoq_id=h['sanoq'], topildi=True).values_list('libos_id', flat=True))
    ortiqcha = topilgan - {h['a'], h['b']}
    return [
        mezon(h['a'] in topilgan, f"{A[0]} {A[1]} belgilandi.", f"{A[0]} {A[1]} hali belgilanmagan."),
        mezon(h['b'] in topilgan, f"{B[0]} {B[1]} belgilandi.", f"{B[0]} {B[1]} hali belgilanmagan."),
        mezon(not ortiqcha, "Faqat ko'rgan liboslaringiz belgilandi.",
              "Javonda ko'rmagan libosingiz ham «topildi» deb belgilangan. Sanoqda faqat qo'lingiz bilan ushlab ko'rganingiz belgilanadi — "
              "ro'yxatdagi «Bekor» bilan qaytaring."),
    ]


def qadamlar(h):
    return ["Menyuda «Liboslar» ni oching va «Sanoq» bo'limiga o'ting.",
            f"«Belgilash» maydoniga {A[0]} deb yozing va «Topildi» ni bosing.",
            f"O'ngdagi «Hali topilmaganlar» ro'yxatida {B[0]} qatoridagi «Topildi» ni bosing."]


def yol(h):
    return [nav('Liboslar'), tab('Sanoq'),
            {'matn': f"Birinchi libosning yorlig'idagi raqamni tering: {A[0]}. (Skaner bo'lsa — skanerlash kifoya.)", 'amal': 'yoz',
             'nishon': {'css': 'input', 'label': 'Artikul'}, 'kutilgan': f'matn:{A[0].lower()}'},
            {'matn': "«Topildi» ni bosing.", 'amal': 'bos', 'nishon': {'css': '.sanoq-kiritish button', 'matn': 'Topildi'},
             'tayyor': {'css': '.sanoq-oxirgi-q', 'ichida': A[0]}},
            {'matn': f"Ikkinchisini ro'yxatdan belgilaymiz: «Hali topilmaganlar» da {B[0]} · {B[1]} qatoridagi «Topildi» ni bosing.",
             'amal': 'bos', 'nishon': {'css': '.sanoq-q', 'ichida': B[0]}, 'ichki': {'css': 'button', 'matn': 'Topildi'},
             'tayyor': {'css': '.sanoq-oxirgi-q', 'ichida': B[0]}}]


DARS = Dars(
    kod='S12', nomi='Sanoqda qatnashish', yonalish='sotuvchi', personaj='madina',
    sahifa='Liboslar → Sanoq',
    vaziyat="Vaqti-vaqti bilan salon javondagi liboslarni sanaydi: tizimda «salonda» deb turgan har bir libos haqiqatan ham "
            "joyidami? Sanoqni rahbar boshlaydi, belgilashda esa hamma yordam beradi — bir necha kishi birga sanasa, tez tugaydi.",
    natija="Sanoq paytida javondagi libosni artikul bo'yicha yoki ro'yxatdan to'g'ri belgilaysiz.",
    xulosa="Ikkala libos belgilandi — kim va qachon belgilagani ham yozildi. Qoida bitta: faqat ko'zingiz bilan ko'rgan buyumni "
           "belgilaysiz. Topilmagan libosni «bor bo'lsa kerak» deb belgilash — sanoqning butun ma'nosini yo'q qiladi. "
           "Sanoqni rahbar yakunlaydi: belgilanmay qolgan liboslar «yo'q» deb chiqadi va u sababini aniqlaydi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=faqat_xodim,
    ishora="Sanoq «Liboslar» bo'limining ichida. Libosni yorlig'idagi artikul bilan topasiz.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
