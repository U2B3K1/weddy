"""S6 — Aksessuar qo'shish. Saqlangan zakazga aksessuar zakaz kartasidan qo'shiladi (Zakazlar.jsx AksessuarForma →
changes.zakazga_aksessuar_qoshish): dona shu kunlarga band bo'ladi, narxi jamiga qo'shiladi. Yangi zakazda esa libos
tanlash qadamidagi «Aksessuarlar» tabidan (YangiZakaz.jsx) — bu yakundagi xulosada aytiladi."""
from apps.catalog.models import Aksessuar, AksessuarDona, Kategoriya
from apps.orders.models import Zakaz, ZakazAksessuar
from apps.orders.services import zakaz_yaratish

from .asos import (BOSHQA_AMALLAR, IJARA, MIJOZ_FIO, MIJOZ_TELEFON, Dars, amal_bolimi, mezon, nav, som, toy_katalogi,
                   zakazni_och)

AKS_NOMI, AKS_NARX = 'Fata', 50_000


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    kat = Kategoriya.objects.create(salon=m.salon, nomi='Aksessuarlar', turi=Kategoriya.Turi.AKSESSUAR, tartib=9)
    a = Aksessuar.objects.create(salon=m.salon, nomi=AKS_NOMI, kod='FT', kategoriya=kat, ijara_narxi=AKS_NARX, qoshgan=m.hamkasb)
    for i in (1, 2):
        AksessuarDona.objects.create(salon=m.salon, aksessuar=a, yorliq=f'FT-0{i}')
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[l['togri'].id])
    return {'zakaz': z.id, 'raqam': z.raqam}


def topshiriq(h):
    return (f"{MIJOZ_FIO} qo'ng'iroq qildi: libosga (#{h['raqam']}-zakaz) fata ham kerak ekan. Zakaziga bitta «{AKS_NOMI}» qo'shing.")


def tekshir(m, javob=None):
    z = Zakaz.objects.filter(salon=m.salon, id=m.holat['zakaz']).first()
    if not z or z.holat == Zakaz.Holat.BEKOR:
        return [mezon(False, '', "Zakaz bekor qilingan. «Qayta boshlash» ni bosing.")]
    soni = ZakazAksessuar.objects.filter(salon=m.salon, zakaz=z).count()
    return [
        mezon(soni == 1, f"Zakazga bitta «{AKS_NOMI}» qo'shildi — u shu kunlarga band.",
              f"«{AKS_NOMI}» hali qo'shilmagan." if soni == 0 else f"Zakazda {soni} ta aksessuar bor, mijozga bitta kerak edi."),
        mezon(z.jami == IJARA + AKS_NARX, f"Jami o'zi yangilandi: {som(IJARA)} + {som(AKS_NARX)} = {som(IJARA + AKS_NARX)}.",
              f"Jami {som(z.jami)} — {som(IJARA + AKS_NARX)} bo'lishi kerak edi."),
    ]


def qadamlar(h):
    return ["Menyuda «Zakazlar» ni oching va mijozning zakazini bosing.",
            "Kartada «Boshqa amallar» ni oching, ichidan «Aksessuarlar» ni tanlang.",
            f"Ro'yxatda «{AKS_NOMI}» tanlangan turibdi — «Qo'shish» ni bosing."]


def yol(h):
    return [nav('Zakazlar'), zakazni_och(MIJOZ_FIO), BOSHQA_AMALLAR, amal_bolimi('Aksessuarlar'),
            {'matn': f"Ro'yxatda shu kunlarga bo'sh aksessuarlar chiqadi. «{AKS_NOMI}» tanlangan — «Qo'shish» ni bosing.",
             'amal': 'bos', 'nishon': {'css': 'details.boshqa-amallar details.amal[open] button', 'matn': "Qo'shish"},
             'tayyor': {'css': '.aks-qator'}}]


DARS = Dars(
    kod='S6', nomi="Aksessuar qo'shish", yonalish='sotuvchi', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi → Boshqa amallar',
    vaziyat="Fata, toj, taqinchoq — bular ham ijaraga beriladi va har bir donasi hisobda turadi. Mijoz libosga qo'shib so'rasa, "
            "uni og'zaki «qo'shib beraman» demang: zakazga yozing — shunda u band bo'ladi va narxi hisobga kiradi.",
    natija="Zakazga aksessuar qo'shasiz: u band bo'ladi va narxi jamiga o'zi qo'shiladi.",
    xulosa=f"«{AKS_NOMI}» zakazga yozildi: shu kunlarga band, narxi jamiga qo'shildi va shartnomada ham chiqadi. Aksessuarni "
           "xuddi shu joydan «Olib tashlash» ham mumkin. Yangi zakaz ochayotganda esa aksessuar libos tanlash qadamida — "
           "toifalar qatoridagi «Aksessuarlar» tabidan qo'shiladi. Libos qaytganda aksessuar ham tekshiriladi: qaytmasa, "
           "«Aksessuar yo'q» deb belgilanadi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    urug=urug, topshiriq=topshiriq, tekshir=tekshir,
    ishora="Saqlangan zakazga qo'shimchalar zakaz kartasidagi «Boshqa amallar» ichida.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
