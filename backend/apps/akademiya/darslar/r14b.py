"""R14B — Jurnal (rahbar). Sozlama → «Jurnal» (components/Jurnal.jsx): kim, qachon, nimani o'zgartirgani (tenants.Jurnal,
oxirgi 200 ta, faqat o'qish) va Telegram xabarlari qaysi xodimga yetib bormagani. Urug'da jurnalga uchta yozuv qo'yiladi,
ulardan biri — rahbar o'rinbosari Kamola libos narxini tushirgani."""
from django.contrib.auth.hashers import make_password

from apps.tenants.models import Xodim, jurnalga_yoz

from .asos import Dars, faqat_rahbar, katalog, nav, savollarni_tekshir, sozlama_qatori

KAMOLA = 'Kamola'

SAVOLLAR = [
    {'matn': "Atlas libosining ijara narxini 300 000 dan 200 000 ga kim tushirgan?",
     'variantlar': [
         ('madina', "Madina", False, "Madina yangi libos qo'shgan — narxni o'zgartirgan u emas. Jurnaldagi qatorni qayta o'qing."),
         ('kamola', KAMOLA, True,
          f"To'g'ri: jurnalda «{KAMOLA} · ijara narxi o'zgardi — M-001 Atlas: 300 000 so'm → 200 000 so'm». Endi uning o'zidan sababini so'raysiz."),
         ('tizim', "Tizim o'zi tushirgan", False, "Tizim narxni o'zi o'zgartirmaydi — har o'zgarishning muallifi jurnalda yoziladi."),
     ]},
    {'matn': "Xodim jurnaldagi o'z yozuvini o'chirib yuborishi mumkinmi?",
     'variantlar': [
         ('ha', "Ha, rahbar ruxsat bersa", False, "Jurnalni hech kim o'zgartira olmaydi — rahbar ham. U faqat o'qish uchun."),
         ('yoq', "Yo'q — jurnal faqat o'qish uchun, uni hech kim o'zgartira olmaydi", True,
          "To'g'ri: shuning uchun unga ishonsa bo'ladi. Ekranda oxirgi 200 ta yozuv ko'rinadi."),
     ]},
    {'matn': "Bir kuni «Telegram xabarlari» blokida shunday yozuv chiqdi: «Madina — Telegram ulamagan, 12 ta xabar yetib bormagan». "
             "Nima qilasiz?",
     'variantlar': [
         ('bot', "Botni qayta ishga tushirishni so'rayman", False, "Bot ishlayapti — xabar Madinaga yetmagan, chunki uning Telegrami ulanmagan."),
         ('ulash', "Madinaga Telegramni ulashni aytaman (yoki Sozlama → Xodimlar dan kod beraman)", True,
          "To'g'ri: ulanmaguncha unga topshirilgan pul tasdig'i va eslatmalar bormaydi."),
     ]},
]


def urug(m):
    katalog(m)
    kamola = Xodim.objects.create(salon=m.salon, ism=KAMOLA, rol=Xodim.Rol.RAHBAR, pin=make_password(None))
    jurnalga_yoz(m.salon, m.hamkasb, 'libos_qoshildi', "M-005 Shohi")
    jurnalga_yoz(m.salon, kamola, 'ijara_narxi_ozgardi', 'M-001 Atlas', 300000, 200000)
    jurnalga_yoz(m.salon, m.xodim, 'sozlama_ozgardi', 'Bron va garov', 'bufer 1 kun', 'bufer 2 kun')
    return {}


def topshiriq(h):
    return ("Atlas libosining ijara narxi 200 000 so'mga tushib qolibdi — siz bunday qaror qilmagansiz. Jurnaldan kim va qachon "
            "o'zgartirganini toping.")


def tekshir(m, javob):
    return savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Jurnal» bo'limiga kiring («Xavfsizlik» guruhida).",
            "Jurnal qidiruviga «Atlas» deb yozing.",
            "Chiqqan qatorda — kim, qachon, eski va yangi qiymat."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Jurnal'),
            {'matn': "Avval jurnal ostidagi blokka qarang — «Telegram xabarlari»: bot xodimlarga yuborgan xabarlar. Biror xodimga "
                     "xabar yetib bormasa, sababi bilan shu yerda yoziladi. O'quv salonida bot ulanmagan — shuning uchun bo'sh.",
             'amal': 'kor', 'nishon': {'css': 'section.soz-panel', 'ichida': 'Telegram xabarlari'}},
            {'matn': "Endi narxni kim o'zgartirganini topamiz. Jurnal qidiruviga libos nomini yozing: Atlas.", 'amal': 'yoz',
             'nishon': {'css': 'input', 'label': 'Jurnaldan qidirish'}, 'kutilgan': 'matn:atlas'},
            {'matn': "Har qatorda: qachon, kim va nima o'zgardi (eski → yangi). Qarab chiqing va savollarga javob bering.",
             'amal': 'kor', 'nishon': {'css': '#soz-jurnal'}}]


def bilim(h):
    return [
        "Jurnal faqat o'qish uchun: undagi yozuvni hech kim — xodim ham, rahbar ham — o'chira yoki o'zgartira olmaydi.",
        "«Telegram xabarlari» blokida «… Telegram ulamagan» yozuvi chiqsa — o'sha xodim Telegramni ulashi kerak "
        "(yoki Sozlama → Xodimlar dan kod berasiz). Ulanmaguncha unga xabarlar bormaydi.",
    ]


DARS = Dars(
    kod='R14B', nomi='Jurnal', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Jurnal',
    vaziyat="Narx o'zgarib qolibdi, libos holati boshqa bo'libdi — kim qildi? Taxmin qilish va xodimlarni so'roqqa tutish "
            "shart emas: tizim har bir muhim o'zgarishni kim va qachon qilganini yozib boradi.",
    natija="Jurnaldan kim, qachon, nimani o'zgartirganini topasiz va Telegram xabarlari kimga yetmaganini ko'rasiz.",
    xulosa="Jurnal — salonning qora qutisi: narx, tannarx, libos holati, sozlamalar, sanoq va qurilma o'zgarishlari, ularning "
           "muallifi va vaqti. Uni hech kim o'zgartira olmaydi. Zakaz bo'yicha o'zgarishlar esa zakaz kartasidagi «O'zgarishlar "
           "tarixi» da. Shu bilan Sozlama bo'limlarining hammasi o'tildi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Jurnal «Xavfsizlik» guruhining oxirida. Qidiruvga ism, libos yoki so'z yozish mumkin.",
    qadamlar=qadamlar, yol=yol, xp=50,
)
