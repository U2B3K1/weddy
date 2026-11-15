"""P5 — Xarajat va pul topshirish (pul bilan ishlaydigan xodim; rahbar bu ishning qabul tomonini R10 da ko'radi).
Kassadan chiqqan har bir so'm yoziladi: xarajat — modda va izoh bilan, rahbar tasdig'ini kutadi (finance.xarajat_kiritish);
rahbarga berilgan naqd — inkassatsiya, rahbar sanab tasdiqlaydi (cash.services.inkassatsiya). Ekranlar: Kassa.jsx XarajatPOS,
InkassatsiyaPOS."""
from apps.cash.models import KassaTopshirish, Tolov
from apps.cash.services import pul_oladimi, smena_ochish, tolov_qabul
from apps.finance.models import Xarajat
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import Xodim

from .asos import AVANS, MIJOZ_FIO, MIJOZ_TELEFON, Dars, mezon, nav, som, tab, toy_katalogi

BOSHLANGICH = 200_000
XARAJAT, TOPSHIRISH = 40_000, 200_000
KASSADA = BOSHLANGICH + AVANS
QOLADI = KASSADA - XARAJAT - TOPSHIRISH


def mos(salon, xodim):
    return xodim.rol != Xodim.Rol.RAHBAR and pul_oladimi(salon, xodim)


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[l['togri'].id])
    s = smena_ochish(salon=m.salon, xodim=m.xodim, boshlangich_qoldiq=BOSHLANGICH)
    tolov_qabul(salon=m.salon, xodim=m.xodim, tur=Tolov.Tur.AVANS, summa=AVANS, zakaz=z)
    return {'smena': s.id, 'rahbar': m.hamkasb.ism}


def topshiriq(h):
    return (f"Kassada {som(KASSADA)} naqd bor. Ikki ish: 1) libosni kimyoviy tozalashga berdingiz va kassadan {som(XARAJAT)} to'ladingiz — "
            f"xarajat qilib yozing; 2) kassada ko'p pul turmasin — {som(TOPSHIRISH)} ni rahbar {h['rahbar']}ga topshiring.")


def tekshir(m, javob=None):
    x = Xarajat.objects.filter(salon=m.salon, kiritgan=m.xodim).order_by('-id').first()
    t = KassaTopshirish.objects.filter(salon=m.salon, kimdan=m.xodim).order_by('-id').first()
    return [
        mezon(x and x.summa == XARAJAT and x.tolov_id, f"Xarajat kassadan yozildi: {som(XARAJAT)}.",
              "Xarajat hali yozilmagan." if not x else f"Xarajat {som(x.summa)} deb yozilgan, to'langani — {som(XARAJAT)}."),
        mezon(x and x.modda == Xarajat.Modda.TOZALASH and x.izoh.strip(), "Moddasi va izohi bor — rahbar nima uchunligini ko'radi.",
              "Xarajat moddasi «Tozalash» bo'lishi va izoh yozilishi kerak: rahbar pul nimaga ketganini shundan biladi."),
        mezon(t and t.rahbarga and t.summa == TOPSHIRISH, f"{som(TOPSHIRISH)} rahbarga topshirildi — u sanab tasdiqlaydi.",
              "Pul hali topshirilmagan." if not t else f"{som(t.summa)} topshirilgan, kerak — {som(TOPSHIRISH)} rahbarga."),
    ]


def qadamlar(h):
    return ["Menyuda «Kassa» ni oching va «Xarajat» bo'limiga o'ting.",
            f"«Tozalash» moddasini tanlang, izoh yozing, klaviaturadan {som(XARAJAT)[:-5]} terib, «xarajatni yozish» ni bosing.",
            "«Inkassatsiya» bo'limiga o'ting: qabul qiluvchi — rahbar.",
            f"Klaviaturadan {som(TOPSHIRISH)[:-5]} terib, «topshirish so'rovini yuborish» ni bosing."]


def yol(h):
    x, t = som(XARAJAT)[:-5], som(TOPSHIRISH)[:-5]
    return [nav('Kassa'), tab('Xarajat'),
            {'matn': "Pul nimaga ketdi? Modda tanlang: «Tozalash».", 'amal': 'bos',
             'nishon': {'css': '.kassa-moddalar button', 'boshi': 'Tozalash'}},
            {'matn': "Izoh yozing — rahbar aynan shuni o'qiydi. Masalan: Zarbof ximchistkaga berildi.", 'amal': 'yoz',
             'nishon': {'css': 'textarea.kassa-maydon'}, 'kutilgan': 'uzunlik:5'},
            {'matn': f"Summani tering: {x}.", 'amal': 'bos', 'nishon': {'css': '.klaviatura'},
             'tayyor': {'css': '.pos-summa b', 'matn': x}},
            {'matn': f"Pastda ko'rinib turibdi: kassada {som(KASSADA)} edi, yozilgach {som(KASSADA - XARAJAT)} qoladi. "
                     "«xarajatni yozish» tugmasini bosing.", 'amal': 'bos',
             'nishon': {'css': 'button.pos-tugma', 'ichida': 'xarajatni yozish'},
             'tayyor': {'css': '.pos-xabar', 'ichida': 'Xarajat kassadan yozildi'}},
            tab('Inkassatsiya'),
            {'matn': f"Qabul qiluvchi — rahbar {h['rahbar']}, u tanlangan. Topshiriladigan summani tering: {t}.", 'amal': 'bos',
             'nishon': {'css': '.klaviatura'}, 'tayyor': {'css': '.pos-summa b', 'matn': t}},
            {'matn': f"Sizda {som(KASSADA - XARAJAT)} bor, topshirilgach {som(QOLADI)} qoladi. «topshirish so'rovini yuborish» ni bosing.",
             'amal': 'bos', 'nishon': {'css': 'button.pos-tugma', 'ichida': "topshirish so'rovini yuborish"},
             'tayyor': {'css': '.pos-xabar', 'ichida': 'Inkassatsiya yozildi'}}]


DARS = Dars(
    kod='P5', nomi='Xarajat va pul topshirish', yonalish='pul', personaj='madina',
    sahifa='Kassa → Xarajat · Inkassatsiya',
    vaziyat="Kassadan pul faqat mijozga garov qaytarish uchun chiqmaydi: ximchistkaga to'lanadi, taksi olinadi, rahbar kunduzgi "
            "naqdni olib ketadi. Har bir chiqim yozilmasa, kechqurun kassa kam chiqadi — va bu sizning kamomadingiz bo'ladi.",
    natija="Kassadan chiqqan pulni xarajat qilib yozasiz va naqdni rahbarga rasmiy topshirasiz.",
    xulosa=f"Ikkala chiqim ham yozildi, kassada {som(QOLADI)} qoldi — tizim ham shuni ko'rsatadi. Xarajat rahbar tasdiqlaguncha "
           "«kutilmoqda» turadi: u rad etsa, summa sizning kamomadingiz hisoblanadi — shuning uchun izohni aniq yozing va chekni "
           "saqlang. Topshirilgan pulni rahbar sanab «qabul qildim» deydi: shundan keyin u pulga rahbar javob beradi. "
           "Smenadagi hamkasbga pul berish ham shu bo'limda.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=mos,
    ishora="Ikkalasi ham «Kassa» bo'limida: «Xarajat» — pul sarflandi, «Inkassatsiya» — pul rahbarga berildi.",
    qadamlar=qadamlar, yol=yol, xp=70,
)
