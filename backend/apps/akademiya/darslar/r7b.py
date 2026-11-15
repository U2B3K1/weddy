"""R7B — Promokod yaratish (rahbar). Sozlama → «Promokodlar» → «Promokod yaratish» (pages/Promokodlar.jsx PromokodForma →
orders/promo.promokod_yaratish). Sotuvchi kodni zakaz kartasida, avans olinguncha qo'llaydi (promo.promokod_qollash);
bitta mijoz kodni standartda bir marta ishlatadi (`bir_mijozga=1`)."""
from apps.orders.models import Promokod

from .asos import Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

KOD, FOIZ = 'TOY10', 10
BIRLIK = {Promokod.ChegirmaTuri.FOIZ: '%', Promokod.ChegirmaTuri.SUMMA: " so'm"}
FORMA = '#soz-promokod .soz-promo-forma'

SAVOLLAR = [
    {'matn': f"Mijoz zakaz berayotib: «Menda {KOD} kodi bor», dedi. Sotuvchi uni qayerga kiritadi?",
     'variantlar': [
         ('kassa', "Pul olayotganda kassada", False,
          "Kassada emas: promokod zakaz narxini o'zgartiradi, shuning uchun avans olinguncha zakaz kartasida kiritiladi."),
         ('karta', "Zakaz kartasida — «Boshqa amallar» → «Promokod», avans olinguncha", True,
          "To'g'ri: kod kiritilishi bilan tizim uni tekshiradi va narxni o'zi kamaytiradi. Avans olingach promokod qo'shilmaydi."),
         ('ogzaki', "Hech qayerga — narxni og'zaki kamaytiradi", False,
          "Og'zaki kamaytirilsa, kod statistikasi ham, kassadagi pul ham to'g'ri chiqmaydi. Kod zakaz kartasida kiritiladi."),
     ]},
    {'matn': f"O'sha mijoz ikki oydan keyin yana keldi va yana {KOD} ni aytdi. Nima bo'ladi?",
     'variantlar': [
         ('ishlaydi', "Kod yana ishlaydi — ko'p martalik-ku", False,
          "Ko'p martalik kodni ko'p mijoz ishlatadi, lekin standartda bitta mijoz — faqat bir marta («Bitta mijozga: 1»)."),
         ('rad', "Tizim rad etadi: bitta mijoz kodni bir marta ishlatadi", True,
          "To'g'ri: «Bitta mijozga» standartda 1. Kerak bo'lsa, kod yaratishda buni oshirish mumkin."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Instagram uchun aksiya: «{KOD}» kodi bilan kelgan mijozga {FOIZ}% chegirma, aksiya bir oy davom etadi. "
            "Shu promokodni yarating.")


def tekshir(m, javob=None):
    p = Promokod.objects.filter(salon=m.salon, kod=KOD).first()
    if not p:
        boshqa = Promokod.objects.filter(salon=m.salon).first()
        return [mezon(False, '', f"Kod boshqa nom bilan yaratilgan: «{boshqa.kod}». Kerak — «{KOD}»." if boshqa
                      else f"«{KOD}» kodi hali yaratilmagan.")] + savollarni_tekshir(SAVOLLAR, javob)
    return [
        mezon(p.chegirma_turi == Promokod.ChegirmaTuri.FOIZ and p.qiymat == FOIZ, f"Chegirma — {FOIZ}%.",
              f"Chegirma {p.qiymat}{BIRLIK.get(p.chegirma_turi, '')} — {FOIZ}% bo'lishi kerak."),
        mezon(p.tugash is not None, f"Muddati bor: {p.tugash:%d.%m.%Y} gacha — keyin o'zi to'xtaydi." if p.tugash else '',
              "Kod muddatsiz yaratilgan — aksiya tugagach ham ishlayveradi. Muddatini «1 oy» qiling."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Promokodlar» bo'limiga kiring.",
            "«Promokod yaratish» ni bosing.",
            f"«Kod» ga {KOD}, «Foiz» ga {FOIZ} yozing, muddatni «1 oy» qiling.",
            "«Yaratish» ni bosing."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Promokodlar'),
            {'matn': "«Promokod yaratish» ni bosing.", 'amal': 'bos', 'nishon': {'css': '#soz-promokod button', 'matn': 'Promokod yaratish'},
             'tayyor': {'css': f'{FORMA} input'}},
            {'matn': f"Kodni yozing: {KOD}. Bo'sh qoldirsangiz, tizim o'zi tasodifiy kod yaratadi.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} label:nth-of-type(2) input'}, 'kutilgan': f'matn:{KOD.lower()}'},
            {'matn': f"«Foiz chegirma» tanlangan. «Foiz» ga yozing: {FOIZ}.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} label:nth-of-type(3) input'}, 'kutilgan': f'raqam:{FOIZ}'},
            {'matn': "Aksiya bir oy: muddat ro'yxatidan «1 oy» ni tanlang.", 'amal': 'yoz',
             'nishon': {'css': f'{FORMA} select:nth-of-type(3)'}, 'kutilgan': 'raqam:1'},
            {'matn': "«Yaratish» ni bosing.", 'amal': 'bos', 'nishon': {'css': f'{FORMA} button', 'matn': 'Yaratish'},
             'tayyor': {'css': '#soz-promokod .soz-kod', 'ichida': KOD}}]


def bilim(h):
    return [
        "Promokodni sotuvchi zakaz kartasida kiritadi: «Boshqa amallar» → «Promokod». Faqat avans olinguncha — keyin qo'shilmaydi.",
        "Bitta mijoz kodni standartda bir marta ishlatadi: ikkinchi safar tizim rad etadi. Kod yaratishda bu sonni oshirish mumkin.",
    ]


DARS = Dars(
    kod='R7B', nomi='Promokod yaratish', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Promokodlar',
    vaziyat="Aksiya e'lon qilmoqchisiz: Instagram'da kod beriladi, u bilan kelgan mijoz chegirma oladi. Kod tizimda yaratilsa, "
            "sotuvchi narxni o'zi kamaytirmaydi va aksiya qancha mijoz olib kelgani ko'rinadi.",
    natija="Muddatli promokod yaratasiz va uni sotuvchi qayerda qo'llashini bilasiz.",
    xulosa=f"«{KOD}» kodi tayyor: bir oy davomida har mijozga bir marta {FOIZ}% chegirma beradi, muddat tugagach o'zi to'xtaydi. "
           "Kodni bossangiz, nechta zakazda ishlatilgani va qancha tushum olib kelgani ko'rinadi; kerak bo'lsa «To'xtatish» yoki "
           "muddatini uzaytirasiz. Kod yaratishda limit, minimal summa va hafta kunlarini ham qo'yish mumkin.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Promokodlar «Narx va chegirma» guruhida. Muddat — «Boshlanish» dan keyingi ro'yxatda.",
    qadamlar=qadamlar, yol=yol, xp=60,
)
