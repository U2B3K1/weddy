"""R2 — Xodim qo'shish (rahbar). Sozlama → Xodimlar: yangi sotuvchi ismi va PIN kodi bilan qo'shiladi."""
from apps.tenants.models import Xodim

from .asos import SAQLANDI, Dars, faqat_rahbar, mezon, nav, sozlama_qatori

YANGI_ISM = 'Sevara'
OYNA = '[role=dialog]'


def urug(m):
    return {}


def topshiriq(h):
    return (f"Salonga yangi sotuvchi keldi — {YANGI_ISM}. Uni tizimga qo'shing: roli «Sotuvchi», PIN kodini 4 ta raqamdan "
            "o'zingiz o'ylab toping (masalan, 4826) va unga ayting.")


def tekshir(m, javob=None):
    x = Xodim.objects.filter(salon=m.salon, ism__iexact=YANGI_ISM).first()
    if not x:
        boshqa = Xodim.objects.filter(salon=m.salon).count() > 2
        return [mezon(False, '', f"Xodim boshqa ism bilan qo'shilgan. Ismi {YANGI_ISM} bo'lishi kerak." if boshqa
                      else f"{YANGI_ISM} hali qo'shilmagan.")]
    return [
        mezon(x.rol == Xodim.Rol.SOTUVCHI, "Roli to'g'ri: sotuvchi.",
              f"Roli «{x.get_rol_display()}» qilib qo'yilgan. Sotuvchiga rahbar roli berilsa, u pul va sozlamalarni ham ko'radi."),
        mezon(x.faol, "Xodim faol — o'z PIN kodi bilan kira oladi.", "Xodim faol emas."),
    ]


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Xodimlar» bo'limiga kiring.",
            "Yuqoridagi «Xodim qo'shish» ni bosing.",
            f"«Ism» ga {YANGI_ISM} deb yozing, «Rol» — «Sotuvchi» turibdi.",
            "«PIN» ga 4–6 raqam kiriting va «Qo'shish» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Xodimlar'),
            {'matn': "«Xodim qo'shish» ni bosing.", 'amal': 'bos',
             'nishon': {'css': 'main button', 'matn': "Xodim qo'shish"}, 'tayyor': {'css': OYNA}},
            {'matn': f"Ismini yozing: {YANGI_ISM}.", 'amal': 'yoz',
             'nishon': {'css': f'{OYNA} label:first-of-type input'}, 'kutilgan': 'uzunlik:3'},
            {'matn': "Rol «Sotuvchi» turibdi — o'zgartirmang. PIN kodini kiriting: 4 ta raqam, faqat u bilishi kerak.", 'amal': 'yoz',
             'nishon': {'css': f'{OYNA} input[type=password]'}, 'kutilgan': 'uzunlik:4'},
            {'matn': "«Qo'shish» ni bosing.", 'amal': 'bos', 'nishon': {'css': f'{OYNA} button', 'matn': "Qo'shish"},
             'tayyor': SAQLANDI}]


DARS = Dars(
    kod='R2', nomi="Xodim qo'shish", yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Xodimlar',
    vaziyat="Yangi sotuvchi ishga chiqdi. U sizning PIN kodingiz bilan ishlamasligi kerak: har bir xodimning o'z ismi va "
            "o'z PIN kodi bo'ladi — shunda kim nima qilgani doim ko'rinadi.",
    natija="Yangi xodimni to'g'ri rol va PIN bilan qo'sha olasiz.",
    xulosa="Xodim qo'shildi: u kirish ekranida o'z ismini tanlab, PIN bilan kiradi. Rol — eng muhim tanlov: sotuvchi faqat "
           "zakaz va (kassa tartibiga qarab) pul bilan ishlaydi, kassir — faqat pul bilan, rahbar — hamma narsani ko'radi. "
           "Xodim ishdan ketsa, shu ro'yxatda uni o'chirib qo'yasiz — zakazlari tarixda qoladi.",
    tekshirilgan='2026-11-13 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir, mos=faqat_rahbar,
    ishora="Xodimlar «Sozlama» bo'limida, «Salon va xodimlar» guruhida boshqariladi.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
