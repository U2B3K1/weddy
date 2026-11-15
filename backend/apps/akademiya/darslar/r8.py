"""R8 — Kechikish jarimasi va avans qaytarish (rahbar). Amalda kechikish jarimasi yoqiladi (kuniga 50 000),
avans qaytarish qoidasi esa standart jadval ustida vaziyat orqali o'rgatiladi.
Qoidalar kod bilan solishtirilgan: rental.py (jarima = kechikkan kun × kunlik summa, qaytarishda o'zi hisoblanadi),
changes.qaytariladigan_foiz va standart_qaytarish_qoidasi ([[30, 100], [7, 50], [0, 0]]), orders.Zakaz.qaytarish_qoidasi
(qoida zakaz yaratilganda qotiriladi)."""
from apps.tenants.models import sozlama

from .asos import SAQLASH, Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, som, sozlama_qatori

SUMMA = 50_000
MAYDON = {'css': 'input', 'label': "Kunlik jarima, so'm"}

SAVOLLAR = [
    {'matn': "Mijoz 1 000 000 so'm avans bergan. To'yiga 10 kun qolganda zakazni bekor qildi. Yuqoridagi qoida bo'yicha "
             "unga qancha qaytariladi?",
     'variantlar': [
         ('hammasi', "1 000 000 so'm — hammasi", False,
          "To'liq qaytarish uchun kamida 30 kun qolgan bo'lishi kerak edi. 10 kun — «7–29 kun» qatoriga tushadi: 50%."),
         ('yarmi', "500 000 so'm — yarmi", True,
          "To'g'ri: 10 kun «7–29 kun» qatoriga tushadi — 50%. Qolgan 500 000 so'm salonda qoladi."),
         ('nol', "Hech narsa", False,
          "Hech narsa qaytmasligi uchun 7 kundan kam qolgan bo'lishi kerak. 10 kun — 50%."),
     ]},
    {'matn': f"Jarimani kuniga {som(SUMMA)} qilib yoqdingiz. Bir hafta o'tib, libos 2 kun kech qaytdi. Qaytarishda nima bo'ladi?",
     'variantlar': [
         ('ozi', f"Tizim {som(2 * SUMMA)} jarimani o'zi hisoblaydi", True,
          f"To'g'ri: kechikkan kun × kunlik summa — 2 × {som(SUMMA)}. Sotuvchi hisoblab o'tirmaydi."),
         ('sotuvchi', "Sotuvchi summani o'zi o'ylab kiritadi", False,
          f"Kiritmaydi: tizim kechikkan kunlarni o'zi sanaydi — 2 × {som(SUMMA)}."),
         ('yoq', "Hech narsa — jarima faqat yangi zakazlarga tegishli", False,
          "Jarima qaytarish paytidagi sozlamaga qarab hisoblanadi: libos 2 kun kechikdi — jarima chiqadi."),
     ]},
    {'matn': "Bugun avans qaytarish qoidasini qattiqroq qildingiz. Kecha rasmiylashtirilgan zakaz ertaga bekor bo'lsa, "
             "unga qaysi qoida qo'llanadi?",
     'variantlar': [
         ('yangi', "Yangi qoida — sozlama hamma zakazga birdan ta'sir qiladi", False,
          "Yo'q: mijoz eski qoida yozilgan shartnomaga imzo qo'ygan. Zakazga yaratilgan kundagi qoida qo'llanadi."),
         ('eski', "Eski qoida — zakaz yaratilgan kundagi", True,
          "To'g'ri: qoida zakaz bilan birga saqlanadi va imzolangan shartnomaga mos qoladi. Yangi qoida — faqat yangi zakazlarga."),
         ('rahbar', "Har safar o'zim qo'lda hal qilaman", False,
          "Shart emas: tizim zakaz yaratilgan kundagi qoidani o'zi qo'llaydi."),
     ]},
]


def urug(m):
    return {}


def topshiriq(h):
    return (f"Liboslar tez-tez kech qaytyapti va keyingi mijozga ulgurmayapti. Kechikish jarimasini yoqing: "
            f"kuniga {som(SUMMA)}.")


def sahna(h):
    return [{'tur': 'ekran', 'sarlavha': 'Sozlama · Avans qaytarish (standart qoida)',
             'matn': "Olib ketishgacha 30 kun va undan ko'p qolgan — avansning 100% qaytadi\n"
                     "7–29 kun qolgan — 50%\n"
                     "7 kundan kam qolgan — 0% (avans salonda qoladi)"}]


def tekshir(m, javob=None):
    s = sozlama(m.salon)
    return [
        mezon(s.kechikish_jarimasi, "Kechikish jarimasi yoqildi va saqlandi.",
              "Kechikish jarimasi hali o'chiq. Almashtirgichni yoqib, pastdagi «Saqlash» ni bosing."),
        mezon(s.kechikish_kunlik_summa == SUMMA, f"Kunlik summa — {som(SUMMA)}.",
              f"Kunlik summa hozir {som(s.kechikish_kunlik_summa)}. {som(SUMMA)} qilib, «Saqlash» ni bosing."),
    ] + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Kechikish jarimasi» bo'limiga kiring.",
            "Sarlavha yonidagi almashtirgichni yoqing.",
            f"«Kunlik summa» ga {SUMMA} yozing va pastdagi «Saqlash» ni bosing.",
            "Avans qaytarish qoidasini o'qib, uchta savolga javob bering."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Kechikish jarimasi'),
            {'matn': "Jarima hozir o'chiq. Sarlavha yonidagi almashtirgichni yoqing.", 'amal': 'bos',
             'nishon': {'css': 'input.soz-switch', 'label': 'Kechikish jarimasi yoqilgan'}, 'tayyor': {'css': '.sozlama-saqlash'}},
            {'matn': f"«Kunlik summa» ga yozing: {SUMMA}. Bu — libos kechikkan har kun uchun.", 'amal': 'yoz',
             'nishon': MAYDON, 'kutilgan': f'raqam:{SUMMA}'},
            SAQLASH]


def bilim(h):
    return [
        "Jarima = kechikkan kun × kunlik summa. Tizim uni qaytarish paytida o'zi hisoblaydi; jarima yoqilgandan keyin kech qaytgan "
        "har bir libosga qo'llanadi.",
        "Avans qaytarish qoidasi — jadval: olib ketishga necha kun qolganda bekor qilinsa, avansning necha foizi qaytadi. "
        "Kerakli qator kunlar soniga qarab topiladi.",
        "Qaytarish qoidasi zakaz bilan birga saqlanadi: qoidani o'zgartirsangiz, eski zakazlar yaratilgan kundagi qoidasi bilan "
        "qoladi.",
    ]


DARS = Dars(
    kod='R8', nomi='Kechikish jarimasi va avans qaytarish', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Zakaz qoidalari',
    vaziyat="Ikki noxush vaziyat bor: mijoz libosni kech qaytaradi yoki zakazni bekor qiladi. Ikkalasida ham «qancha pul» "
            "degan savolga sotuvchi emas, oldindan yozilgan qoida javob berishi kerak — shunda tortishuv bo'lmaydi.",
    natija="Kechikish jarimasini sozlay olasiz va bekor qilingan zakazda avans qancha qaytishini ayta olasiz.",
    xulosa=f"Jarima yoqildi: libos kech qaytsa, tizim kechikkan kun × {som(SUMMA)} ni qaytarish paytida o'zi hisoblaydi va bu "
           "shartnomaga ham band bo'lib yoziladi. Avans qaytarish qoidasi yonidagi «Avans qaytarish» bo'limida: kunlar va "
           "foizlarni o'zingizga moslaysiz. Har ikki qoida mijoz imzolaydigan shartnomada chiqadi, qaytarish qoidasi esa "
           "zakaz yaratilgan kuni qanday bo'lsa, o'sha zakaz uchun shunday qoladi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, sahna=sahna, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Jarima «Sozlama → Kechikish jarimasi» da: avval almashtirgich yoqiladi, keyin summa yoziladi.",
    qadamlar=qadamlar, yol=yol, xp=70,
)
