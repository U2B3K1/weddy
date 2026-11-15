"""S5 — Vaqtinchalik bron. Avanssiz zakaz libosni cheklangan vaqtga ushlab turadi (SalonSozlamalari.vaqtinchalik_bron_soat,
standart 24 soat); muddat o'tsa zakaz o'zi bekor bo'ladi va libos bo'shaydi (changes.muddati_otganlarni_bekor_qil).
Avans bronni mustahkamlaydi (cash.services.tolov_qabul); sanani ko'chirish muddatni uzaytirmaydi (changes.sanani_kochirish)."""
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import sozlama

from .asos import MIJOZ_FIO, MIJOZ_TELEFON, Dars, nav, savollarni_tekshir, toy_katalogi, zakazni_och


def urug(m):
    l, dan, gacha = toy_katalogi(m)
    z = zakaz_yaratish(salon=m.salon, xodim=m.xodim, telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, olib_ketish=dan,
                       qaytarish=gacha, libos_idlari=[l['togri'].id])
    return {'raqam': z.raqam, 'soat': sozlama(m.salon).vaqtinchalik_bron_soat}


def savollar(h):
    soat = h['soat']
    return [
        {'matn': "Mijoz: «Ertaga kelib avans beraman», deb ketdi. Zakaz qachongacha uning nomida turadi?",
         'variantlar': [
             ('toy', "To'y kunigacha — zakaz yozildi-ku", False,
              f"Yo'q: avanssiz zakaz faqat {soat} soat turadi. Aniq vaqti zakaz kartasining tepasida yozilgan."),
             ('muddat', f"Kartada yozilgan vaqtgacha — {soat} soat; keyin o'zi bekor bo'ladi", True,
              f"To'g'ri: avans olinmasa, {soat} soatdan keyin tizim zakazni o'zi bekor qiladi. Mijozga shu vaqtni aniq ayting."),
             ('men', "Men o'zim bekor qilmagunimcha", False,
              f"Tizim kutmaydi: {soat} soat o'tgach zakaz o'zi bekor bo'ladi — siz hech narsa bosmasangiz ham."),
         ]},
        {'matn': "Muddat o'tdi, mijoz kelmadi — zakaz o'zi bekor bo'ldi. Libos bilan nima bo'ladi?",
         'variantlar': [
             ('band', "Baribir shu mijozga band turadi", False,
              "Yo'q: bron bekor bo'lishi bilan libos bo'shaydi. Mijoz keyinroq kelsa, libos boshqaga ketgan bo'lishi mumkin."),
             ('boshaydi', "Bo'shaydi — o'sha kunlarga boshqa mijoz olishi mumkin", True,
              "To'g'ri: vaqtinchalik bronning ma'nosi shu — va'da berib kelmagan mijoz libosni to'sib turmaydi."),
             ('tozalash', "Tozalashga o'tadi", False, "Libos salondan chiqmagan — tozalash kerak emas. U shunchaki bo'shaydi."),
         ]},
        {'matn': "Mijoz libosni aniq olmoqchi. Bron o'zi bekor bo'lmasligi uchun nima qilinadi?",
         'variantlar': [
             ('vada', "Mijoz so'z bersa yetarli", False,
              "Tizim so'zni bilmaydi. Bronni faqat avans mustahkamlaydi."),
             ('kochir', "Sanani har kuni ko'chirib, muddatni uzaytiraman", False,
              "Ishlamaydi: sana ko'chirilganda ham muddat o'sha-o'sha qoladi. Bronni faqat avans mustahkamlaydi."),
             ('avans', "Avans olinadi — zakaz «Bron» holatiga o'tadi", True,
              "To'g'ri: avans yozilishi bilan bron mustahkam bo'ladi va endi o'zi bekor bo'lmaydi."),
         ]},
    ]


def topshiriq(h):
    return (f"{MIJOZ_FIO} libos tanladi, lekin avans bermadi (#{h['raqam']}-zakaz). Zakazini oching: tepasida bron qachongacha "
            "turishi yozilgan. Shunga qarab, uchta savolga javob bering.")


def tekshir(m, javob):
    return savollarni_tekshir(savollar(m.holat), javob)


def qadamlar(h):
    return ["Menyuda «Zakazlar» ni oching va mijozning zakazini bosing.",
            "Sarlavha yonida holat — «Vaqtinchalik». Uning ostida: «… gacha avans olinmasa, bron o'zi bekor bo'ladi».",
            "Shu vaqt — mijozga aytadigan muddatingiz."]


def yol(h):
    return [nav('Zakazlar'), zakazni_och(MIJOZ_FIO),
            {'matn': "Sarlavhaga qarang: holat — «Vaqtinchalik», ostida esa bron qachongacha turishi yozilgan. "
                     "Savollarga javob bering.", 'amal': 'kor', 'nishon': {'css': '.karta-bosh'}}]


def bilim(h):
    return [
        "Avanssiz zakaz — vaqtinchalik bron: kartada yozilgan vaqtgacha turadi, keyin tizim uni o'zi bekor qiladi.",
        "Bekor bo'lgach libos bo'shaydi — o'sha kunlarga boshqa mijoz olishi mumkin.",
        "Bronni mustahkam qilishning yo'li bitta — avans: u yozilishi bilan zakaz «Bron» holatiga o'tadi va o'zi bekor bo'lmaydi.",
    ]


DARS = Dars(
    kod='S5', nomi='Vaqtinchalik bron', yonalish='sotuvchi', personaj='madina',
    sahifa='Zakazlar → zakaz kartasi',
    vaziyat="Mijoz libosni tanladi-yu, puli yonida yo'q ekan: «Ertaga kelaman», deydi. Zakazni yozib qo'ysangiz, libos unga "
            "band bo'ladi. Lekin u kelmasa-chi? Libos bekorga turib qolmasligi uchun tizimda muddat bor.",
    natija="Avanssiz bron qancha turishini mijozga aniq aytasiz va uni qanday mustahkamlashni bilasiz.",
    xulosa="Avanssiz zakaz — vaqtinchalik bron: muddat o'tsa, tizim uni o'zi bekor qiladi va libos bo'shaydi. Muddat zakaz kartasida "
           "va Zakazlar ro'yxatida («avans … gacha») ko'rinib turadi. Mijoz kech qolayotgan bo'lsa — qo'ng'iroq qiling. "
           "Avans olingan zahoti bron mustahkamlanadi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=savollar,
    ishora="Zakaz kartasining eng tepasiga qarang — muddat o'sha yerda.",
    qadamlar=qadamlar, yol=yol, xp=40,
)
