"""R5 — Libos qo'shish va tasdiqlash (rahbar). Rahbar qo'shgan libos darhol katalogga chiqadi — narx va tannarx bilan
(Katalog.jsx LibosForma); sotuvchi qo'shgani esa rahbar narx va tannarxni tasdiqlaguncha «Tasdiq kutmoqda» da turadi
(TasdiqForma → catalog.services.libosni_tasdiqlash). Tannarx — libos o'zini oqladimi degan savolning asosi (hisobotlar)."""
from apps.catalog.models import Kategoriya, Libos
from apps.tenants.models import sozlama

from .asos import Dars, faqat_rahbar, katalog, mezon, nav, som

NOMI, TOIFA, OLCHAM, NARX, TANNARX = 'Marvarid', "Oq ko'ylak", '46', 400_000, 4_000_000
K_ARTIKUL, K_NOMI, K_NARX, K_TANNARX = 'M-005', 'Shohi', 350_000, 3_500_000
FORMA = '[role=dialog]'
XABAR = '.libos-sahifa > p.malumot'


def urug(m):
    s = sozlama(m.salon)  # artikulni tizim o'zi beradi — o'quvchi faqat mazmunni kiritadi
    s.artikul_avto, s.artikul_prefiks = True, 'L-'
    s.save(update_fields=['artikul_avto', 'artikul_prefiks'])
    katalog(m)
    k = Libos.objects.create(salon=m.salon, kategoriya=Kategoriya.objects.get(salon=m.salon, nomi='Milliy'), artikul=K_ARTIKUL,
                             nomi=K_NOMI, olcham='44', ijara_narxi=K_NARX, zalog=100_000, qoshgan=m.hamkasb,
                             holat=Libos.Holat.TASDIQ_KUTILMOQDA)
    return {'kutayotgan': k.id, 'sotuvchi': m.hamkasb.ism}


def topshiriq(h):
    return (f"Ikki ish. 1) Salonga yangi libos keldi — katalogga qo'shing: «{NOMI}», {TOIFA.lower()}, {OLCHAM}-o'lcham, ijarasi "
            f"{som(NARX)}, sotib olingan narxi (tannarx) {som(TANNARX)}. 2) {h['sotuvchi']} qo'shgan {K_ARTIKUL} {K_NOMI} libosi "
            f"tasdig'ingizni kutyapti: tannarxi {som(K_TANNARX)} — tasdiqlang.")


def tekshir(m, javob=None):
    yangi = Libos.objects.filter(salon=m.salon, qoshgan=m.xodim).order_by('-id').first()
    k = Libos.objects.filter(salon=m.salon, id=m.holat['kutayotgan']).first()
    return [
        mezon(yangi and yangi.holat == Libos.Holat.BOSH, "Yangi libos katalogga qo'shildi — uni endi zakazga yozish mumkin.",
              "Yangi libos hali qo'shilmagan."),
        mezon(yangi and (yangi.ijara_narxi, yangi.tannarx) == (NARX, TANNARX), f"Narxlari to'g'ri: ijara {som(NARX)}, tannarx {som(TANNARX)}.",
              f"Narxlar mos emas: ijara {som(NARX)}, tannarx {som(TANNARX)} bo'lishi kerak." if yangi else "Narxlar hali kiritilmagan."),
        mezon(yangi and yangi.kategoriya.nomi == TOIFA and yangi.olcham.strip() == OLCHAM, f"Toifa va o'lcham to'g'ri: {TOIFA.lower()}, {OLCHAM}.",
              f"Toifa «{TOIFA}», o'lcham {OLCHAM} bo'lishi kerak — sotuvchi libosni shular bo'yicha topadi." if yangi else "Toifa va o'lcham hali kiritilmagan."),
        mezon(k and k.holat == Libos.Holat.BOSH and k.tannarx == K_TANNARX, f"{K_ARTIKUL} {K_NOMI} tasdiqlandi va katalogga chiqdi.",
              f"{K_ARTIKUL} {K_NOMI} hali tasdiqlanmagan." if not k or k.holat != Libos.Holat.BOSH
              else f"Tannarx {som(k.tannarx or 0)} deb yozilgan — {som(K_TANNARX)} bo'lishi kerak edi."),
    ]


def qadamlar(h):
    return ["Menyuda «Liboslar» ni oching va «Libos qo'shish» ni bosing.",
            f"Nomi — {NOMI}, kategoriya — {TOIFA}, o'lcham — {OLCHAM}, ijara narxi — {NARX}, tannarx — {TANNARX}. «Qo'shish» ni bosing.",
            f"Sahifa tepasidagi «Tasdiq kutmoqda» blokida {K_ARTIKUL} {K_NOMI} uchun tannarxga {K_TANNARX} yozing.",
            "«Tasdiqlash» ni bosing."]


def yol(h):
    return [nav('Liboslar'),
            {'matn': "«Libos qo'shish» ni bosing.", 'amal': 'bos', 'nishon': {'css': 'button.bosh-tugma', 'ichida': "Libos qo'shish"},
             'tayyor': {'css': f'{FORMA} .libos-forma'}},
            {'matn': f"Nomini yozing: {NOMI}. Artikulni tizim o'zi beradi.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} input', 'placeholder': 'Oq atlas'}, 'kutilgan': 'uzunlik:4'},
            {'matn': f"Kategoriyani tanlang: «{TOIFA}».", 'amal': 'bos', 'nishon': {'css': f'{FORMA} [role=radio]', 'matn': TOIFA}},
            {'matn': f"O'lchamini yozing: {OLCHAM}.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} input', 'placeholder': 'masalan: 44'}, 'kutilgan': f'raqam:{OLCHAM}'},
            {'matn': f"Ijara narxi — mijoz to'laydigan summa: {NARX}.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} fieldset.lf-bolim:nth-of-type(2) .libos-narxlar > label:nth-child(1) input'},
             'kutilgan': f'raqam:{NARX}'},
            {'matn': f"Tannarx — libosni o'zingiz qanchaga olgansiz: {TANNARX}. Uni faqat rahbar ko'radi.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} label.lf-tannarx input'}, 'kutilgan': f'raqam:{TANNARX}'},
            {'matn': "Tizim hisoblab berdi: libos taxminan 10 ta ijarada o'zini oqlaydi. «Qo'shish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': f'{FORMA} button.pos-tugma'}, 'tayyor': {'css': XABAR, 'ichida': "katalogga qo'shildi"}},
            {'matn': f"Endi ikkinchi ish. Tepada «Tasdiq kutmoqda»: {h['sotuvchi']} qo'shgan {K_ARTIKUL} {K_NOMI}. U ijara narxini yozgan, "
                     f"tannarxni esa faqat siz bilasiz. «Tannarx» ga yozing: {K_TANNARX}.", 'amal': 'yoz',
             'nishon': {'css': '.tasdiq .libos-narxlar > label:nth-child(2) input'}, 'kutilgan': f'raqam:{K_TANNARX}'},
            {'matn': "«Tasdiqlash» ni bosing — libos katalogga chiqadi.", 'amal': 'bos',
             'nishon': {'css': '.tasdiq button', 'matn': 'Tasdiqlash'}, 'tayyor': {'css': XABAR, 'ichida': 'katalogga chiqdi'}}]


DARS = Dars(
    kod='R5', nomi="Libos qo'shish va tasdiqlash", yonalish='rahbar', personaj='nodira',
    sahifa='Liboslar → Libos qo\'shish · Tasdiq kutmoqda',
    vaziyat="Katalog — salonning asosiy mulki. Unga libos ikki yo'l bilan tushadi: o'zingiz qo'shasiz yoki sotuvchi qo'shadi, "
            "siz tasdiqlaysiz. Ikkalasida ham bitta raqam faqat sizniki: tannarx. U bo'lmasa, tizim foydani noto'g'ri ko'rsatadi.",
    natija="Katalogga libosni narxi va tannarxi bilan qo'shasiz va sotuvchi qo'shgan libosni tasdiqlaysiz.",
    xulosa="Ikkala libos ham katalogda. Tannarxni kiritganingiz uchun tizim endi har libos nechta ijarada o'zini oqlashini va oylik "
           "foydani to'g'ri hisoblaydi; tannarxsiz libos haqida qo'ng'iroqcha eslatib turadi. Haqiqiy ishda libosga 3–5 ta rasm ham "
           "qo'shing — mijozga planshetdan ko'rsatiladi. Sotuvchilar libos qo'sha olmasligi kerak bo'lsa — Sozlama → "
           "«Libos qo'shish va manekin».",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=faqat_rahbar,
    ishora="Ikkalasi ham «Liboslar» bo'limida: «Libos qo'shish» tugmasi va sahifa tepasidagi «Tasdiq kutmoqda» bloki.",
    qadamlar=qadamlar, yol=yol, xp=80,
)
