"""Darslar ro'yxati. Yangi dars: shu papkada fayl (`DARS = Dars(...)`) va pastdagi ro'yxatga bitta qator.
Tartib — o'quv yo'lidagi tartib (yo'nalish ichida)."""
from . import (k1, k2, k3, k4, p1, p2, p5, p6, r1, r2, r3, r3b, r4, r4b, r4c, r5, r5b, r6, r6b, r7, r7b, r7c, r8, r8b, r8c,
               r9, r10, r11, r12, r12b, r13, r13b, r14, r14b, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12)
from .asos import PERSONAJLAR, YONALISHLAR, Dars, Muhit, daraja  # noqa: F401 — tashqariga beriladi

DARSLAR = [
    # Tanishuv
    k1.DARS, k2.DARS, k3.DARS, k4.DARS,
    # Mijoz va zakaz
    s1.DARS, s2.DARS, s3.DARS, s4.DARS, s5.DARS, s6.DARS, s7.DARS, s8.DARS, s9.DARS, s10.DARS, s11.DARS, s12.DARS,
    # Pul va kassa
    p1.DARS, p2.DARS, p5.DARS, p6.DARS,
    # Salonni boshqarish: avval ishga tushirish va xavfsizlik, keyin xodimlar va katalog, zakaz va narx qoidalari,
    # oxirida nazorat va xabarlar
    r1.DARS, r3.DARS, r3b.DARS, r2.DARS, r4.DARS, r4b.DARS, r4c.DARS, r5.DARS, r5b.DARS,
    r6.DARS, r6b.DARS, r7.DARS, r7b.DARS, r7c.DARS, r8.DARS, r8b.DARS, r8c.DARS,
    r9.DARS, r10.DARS, r11.DARS, r12.DARS, r12b.DARS, r13.DARS, r13b.DARS, r14.DARS, r14b.DARS,
]
DARS = {d.kod: d for d in DARSLAR}

# Akademiya tizimni boshidan oxirigacha o'rgatadi (ega talabi, 2026-11-13). Hali yozilmagan darslar shu ro'yxatga
# (kod, nomi, yo'nalish) bo'lib yoziladi va xaritada «Tez orada» deb ko'rinadi; yozilgach DARSLAR ga o'tadi.
# 2026-11-14: rejadagi hamma dars yozildi — ro'yxat bo'sh.
REJA = []

# O'quv yo'li boblari (ega talabi, 2026-11-14: yo'l hikoyali boblar bo'lib ko'rinsin). Har bob — bitta sahna-banner
# (`frontend/public/akademiya/bob-<kalit>.jpg`), nomi, «// nima qilasiz» shiori, qisqa izoh va voqea — bobdan bobga
# davom etadigan hikoya (Madinaning birinchi kunidan Nodiraning salonni masofadan kuzatishigacha). Darslar tartibi DARSLAR
# dagi bilan bir xil; o'quvchiga mos darsi qolmagan bob ko'rsatilmaydi (masalan, sotuvchiga rahbar boblari).
BOBLAR = [
    ('birinchi-kun', 'Birinchi kun', 'salon bilan tanishasiz',
     "Tizimga kirasiz, bugungi ishlarni topasiz va pulning to'rt turini ajratasiz.",
     "Madinaning birinchi ish kuni. Nodira opa unga kalitni berdi va dedi: «Avval tizimga kirishni va bugun nima qilish kerakligini topishni o'rgan — qolgani shundan boshlanadi».",
     ['K1', 'K2', 'K3', 'K4']),
    ('mijoz-keldi', 'Mijoz keldi', 'birinchi zakazni yozasiz',
     "Mijozga bo'sh libos topasiz va zakazni boshidan oxirigacha o'zingiz yaratasiz.",
     "Eshik ochildi: Nilufar onasi bilan to'y libosini izlab keldi. Sana aniq, vaqt oz — Madina bo'sh libosni topib, birinchi zakazini yozishi kerak.",
     ['S1', 'S2', 'S3', 'S4']),
    ('tanlov', 'Tanlov', 'bron, aksessuar va chegirma',
     "Sanani band qilasiz, aksessuar qo'shasiz va chegirmani to'g'ri so'raysiz.",
     "Nilufar libosni tanladi, lekin hali o'ylab ko'rmoqchi. Fata va toj ham kerak, onasi esa chegirma so'rayapti. Madina hammasini qoida bo'yicha qilishi kerak.",
     ['S5', 'S6', 'S7']),
    ('toy-kuni', "To'y kuni", 'libosni topshirasiz va qaytarib olasiz',
     "Libosni berasiz, qaytarib olasiz, kechikkan va o'zgargan zakazni yakunlaysiz.",
     "To'y kuni yetib keldi: libos tayyor, mijoz eshik oldida. Topshirish, qaytarib olish, kechikkanlar — bu yerda bitta unutilgan qadam salonga qimmatga tushadi.",
     ['S8', 'S9', 'S10', 'S11', 'S12']),
    ('kassa', 'Kassa', 'pulni xatosiz sanaysiz',
     "Smenani ochasiz, to'lov qabul qilasiz, xarajat yozasiz va kunni yopasiz.",
     "Kech kirdi, salon bo'shadi. Endi pul sanaladi: har so'm qayerdan kelgani va qayerga ketgani aniq bo'lmaguncha kun yopilmaydi.",
     ['P1', 'P2', 'P5', 'P6']),
    ('salon', 'Salon sizniki', "salonni yo'lga qo'yasiz",
     "Xodimlar, qurilmalar, kassa tartibi va filiallarni sozlaysiz.",
     "Nodira tizimni salonga o'zi olib keldi. Avval tartib: kim kiradi, qaysi qurilmadan, pulni kim oladi. Bir marta to'g'ri sozlansa, keyin tizim uning o'rniga kuzatadi.",
     ['R1', 'R3', 'R3B', 'R2', 'R4', 'R4B', 'R4C']),
    ('libos', 'Yangi libos', 'libos va narxni belgilaysiz',
     "Libos qo'shasiz, bron va garov qoidalarini, chegirma va ustamalarni o'rnatasiz.",
     "Yangi kolleksiya keldi. Har libosning narxi, garovi va tozalash kuni bor — ularni rahbar belgilaydi, sotuvchi esa faqat tanlaydi.",
     ['R5', 'R5B', 'R6', 'R6B', 'R7', 'R7B', 'R7C']),
    ('kelishuv', 'Kelishuv', "qoidalarni yozib qo'yasiz",
     "Kechikish jarimasi, avans qaytarish va shartnoma bandlari — tortishuv chiqmasligi uchun.",
     "Bir mijoz zakazni bekor qilib, avansni to'liq qaytarishni talab qildi. Qoida oldindan yozib qo'yilgan bo'lsa, tortishuvga o'rin qolmaydi.",
     ['R8', 'R8B', 'R8C']),
    ('yakun', 'Kun yakuni', 'pul va libosni tekshirasiz',
     "Smena farqini topasiz, pul topshirishni qabul qilasiz, sanoq va hisobotlarni ko'rasiz.",
     "Kecha kassada ellik ming so'm yetmadi. Kim xato qildi? Taxmin qilish shart emas — tizim hammasini ko'rsatadi.",
     ['R9', 'R10', 'R11', 'R12', 'R12B']),
    ('nazorat', 'Hammasi nazoratda', 'xabarlar va xavfsizlik',
     "Bot, SMS, yordam va jurnal: salon siz yo'g'ingizda ham ko'z ostida.",
     "Nodira bir hafta salonda bo'lmaydi. Telefoniga keladigan xabarlar va jurnal bilan u hamma narsadan xabardor.",
     ['R13', 'R13B', 'R14', 'R14B']),
]

assert [k for *_, kodlar in BOBLAR for k in kodlar] == [d.kod for d in DARSLAR], "BOBLAR dagi darslar DARSLAR tartibiga mos emas"
assert len(DARS) == len(DARSLAR), 'Dars kodi takrorlangan'
assert not {k for k, _, _ in REJA} & set(DARS), 'Yozilgan dars REJA da qolib ketgan'
assert all(d.yonalish in dict(YONALISHLAR) and d.personaj in PERSONAJLAR for d in DARSLAR), "Noma'lum yo'nalish yoki personaj"
assert all(y in dict(YONALISHLAR) for _, _, y in REJA), "REJA da noma'lum yo'nalish"
