# UX uslubi — foydalanuvchi maketi («DressRent Pro») asosida

> 2026-11-07, `claude`. Manba: foydalanuvchi bergan dashboard maketi (rasm). Birinchi qo'llangan joy — rahbar Dashboard'i
> (`pages/Dashbord.jsx`, `ichki.css` → «Dashboard (rahbar)»). Keyingi bo'limlar shu qo'llanma bo'yicha moslanadi.
> **Ranglar maketdagidek yorug' emas** — loyihaning o'z uslubi saqlanadi: tungi fon, tilla (`--tilla`), serif sarlavha (Forum),
> matn Spectral, kursiv yorliq (Cormorant). Maketdan **tuzilma, o'lcham nisbatlari va komponentlar** olinadi.

## 1. Sahifa tuzilmasi
- Chapda doimiy menyu, tepada panel: sahifa nomi · keng qidiruv · qo'ng'iroqcha · xodim. Qo'ng'iroqcha — barcha
  «hozir nima qilish kerak» xabarlari (qarorlar, bugungi ishlar, ogohlantirishlar) va pastida Telegram ulash.
- Kontent — **kartalar to'ri**, keng ekranda butun enni egallaydi (Dashboard: `main` 1720 px gacha; maketda bo'sh yon joy yo'q).
- Qatorlar ustunlari maketdagi nisbatda (`fr` bilan): ko'rsatkichlar 4 teng; ish qatorlari 512 : 479 : 277 va 345 : 302 : 351 : 263.
  O'ng ustun — qisqa ro'yxat va tezkor amallar. 1279 px dan pastda 2 ustun, 899 px dan pastda 1 ustun.
- Oraliqlar bir xil (`--o-4` = qatorlar va kartalar orasida), karta ichida `--o-3`.

## 2. Komponentlar (mavjud sinflar)
| Komponent | Maketdagi ko'rinishi | Loyihada | Qoida |
|---|---|---|---|
| Ko'rsatkich kartasi | rangli plitka-belgi, katta son, nom, o'ng tepada ↑/↓ % | `.dash-kpi-karta`, `.kpi-plitka.{tilla,yashil,kok,pushti}`, `.trend-pill.{osish,tushish}` | Foiz — faqat oldingi **teng** davrga nisbatan; oldingi 0 bo'lsa «yangi». Izoh bir qatorda |
| Karta sarlavhasi | belgi + qalin nom chapda, «Barchasi →» o'ngda, kerak bo'lsa davr tanlovi | `KartaBosh` (`.dash-karta-bosh`) | Nom serif 20 px; havola qisqa («45 ta →») |
| Ro'yxat qatori | avatar, ism qalin, ikkinchi qator (libos/sana), o'ngda holat belgisi | `.dash-bron-royxat`, `.dash-avatar`, `.holat-pill.{bron,vaqt,yopiq}` | Butun qator — bitta tugma (zakaz kartasini ochadi) |
| Rasmli karta | rasm, o'rin belgisi (#1), nom, «Ijara: N marta», narx | `.dash-mashhur-tor`, `.dash-orin`, `LibosSiluet` | Rasm bo'lmasa — tilla siluet |
| Halqa diagramma | markazda jami, yonida rangli nuqtali legenda va foiz | `components/Halqa.jsx`, `.dash-legenda` | Rang + son + foiz (faqat rangga tayanmaslik) |
| Chiziqli grafik | maydon to'ldirilgan chiziq, nuqta ustida izoh | `components/TushumChizigi.jsx` | Oldingi davr — uzuq chiziq; ← → bilan ham ishlaydi |
| Tezkor amallar | 2×2 plitka: belgi ustida, nom ostida | `.dash-tez-tor`, `.dash-tez-tugma` | Har biri aniq amal ochadi (masalan, «Libos qo'shish» — oynani) |
| Holat belgisi | yumshoq fonli kichik «pill» | `.holat-pill` | Yashil — tasdiqlangan/bron, sariq — kutilmoqda, qizil — qarz/kechikkan, kulrang — yopiq |

## 3. Tipografiya va rang
- Son va summalar — serif (Forum), `tabular-nums`; asosiy summa tilla, qolgani oq.
- Yorliqlar — Cormorant kursiv 15–16 px; ikkinchi darajali matn `--matn-3` (AA kontrast).
- Plitka ranglari faqat belgi uchun (8–14% shaffof fon): tilla — pul, yashil — zakaz, ko'k — libos, pushti — mijoz.

## 4. Boshqa bo'limlarni moslash rejasi — 2026-11-08 hammasi bajarildi
| Bo'lim | Nima qilinadi |
|---|---|
| Zakazlar ✅ (2026-11-08) | Tepada 4 **ko'rsatkich kartasi-filtr** (Bugun olib ketadi · Bugun qaytaradi · Kechikkan · To'lov kutmoqda): bosilsa ro'yxat filtrlanadi, yana bosilsa «Faol»; olib/qaytar kartasida «ertaga — N ta» ham filtr. Eski «Bugun» tasmasi olib tashlandi. Ro'yxat (tablar, qidiruv, jadval) — o'zgarmagan, karta ichida. O'ngda «Bugun» ustuni (avatar qatorlari: olib ketadi + qoldiq, qaytaradi, kechikkan) — **faqat ≥1440 px** (1280 da jadvalning «Jami» ustuni sig'masdi). Telefonda kartalar ixcham (2×2, belgi yonida). Sahifa keng ekranda 1720 px gacha. Umumiy qatorlar: `components/ZakazQatorlari.jsx` (`Qatorlar`, `Belgi` — bosh sahifa bilan bir xil). Backend: `GET /zakazlar/sonlar/` ga `tolov_kutmoqda` |
| Liboslar ✅ (2026-11-08) | Tepada 4 ko'rsatkich kartasi-filtr (Faol liboslar + o'rtacha ijara · Ijaraga tayyor + % · Mijozda + eng yaqin qaytish · Ta'mir va tozalashda) — eski 5 ta kichik stat o'rnida. ≥1280 px da chapda filtr ustuni (250 px, sticky): Kategoriya, O'lcham (chiplar), Holat — yonida soni (boshqa filtrlar hisobga olingan), soni 0 holatlar yashirin, «Filtrlarni tozalash»; torroqda filtrlar avvalgidek asboblar panelida (tablar, tanlov, chiplar — `.tor-filtr`). Libos kartochkalari o'zgarmagan. Rang bo'yicha filtr qo'shilmadi (ma'lumot to'liq emas) |
| Mijozlar ✅ (2026-11-08) | Rahbarga tepada 4 ko'rsatkich kartasi-filtr: Jami mijozlar (+ qora ro'yxatdagilar) · Yangi (birinchi zakazi 30 kunda) · Yaqin to'ylar (30 kun ichida) · Qarzdorlar (jami qarz) — panel sarlavhasi filtr nomini oladi. Backend: `GET /api/mijozlar/sonlar/` (rahbar), ro'yxatga `?tur=yangi|toy|qarzdor`. Sotuvchiga kartalar yo'q (u ro'yxatni ko'rmaydi, faqat qidiradi). Ro'yxat jadvali avatar bilan avvaldan; o'ngda mijoz varaqasi (master-detail) qilinmadi — karta to'liq sahifa varaqasi, alohida ish |
| Kassa ✅ (2026-11-08) | «Smena hisoboti» tepasida 4 ko'rsatkich (bosilmaydi): Kassada naqd (+ kun boshida) · Kirgan naqd · Terminal (tizimdagi, chek bilan solishtirish) · Chiqim (xarajat + topshirilgan); summa yaxlitlanmaydi — so'mgacha aniq (kassada «2 mln» 1 990 000 ni yashirardi). Ostida «Kun yakuni» va «Naqd pul hisobi» yonma-yon. `KpiFiltr` `onBos`siz — oddiy ko'rsatkich. Smena paneli, To'lov qabul (POS), Xarajat, Inkassatsiya, Zaloglar — POS tuzilmasi o'zgarmadi: ular klaviatura bilan ishlaydigan ish joyi, kartalar to'riga mos emas |
| Hisobotlar ✅ (2026-11-08) | **Oylik foyda:** tepada 4 ko'rsatkich — Tushum · Xarajatlar · Foyda/Zarar · Foyda ulushi; tushum va foyda o'tgan oyning shu kunigacha bilan taqqoslanadi (`taqqos.otgan_oy`). **Umumiy hisobot:** har turning jami qatoridan 2–4 ta pul/son ustuni ko'rsatkich bo'ladi, oldingi teng davr (`[dan−N, dan−1]`) bilan; davrsiz hisobotlarda taqqoslash yo'q, bitta raqamli hisobotda kartalar chiqmaydi. Taqqoslash belgisi rangsiz (xarajat o'sishi yomon, tushum o'sishi yaxshi — hukm o'quvchida); manfiy qiymatga «yangi» yozilmaydi. Torroq sahifada (1180 px) kartalar 2×2 (≥1440 px da 4 ta qatorda). Jadvallar o'zgarmadi; `TushumChizigi` qo'llanmadi (Oylik foyda'da 12 oylik ustunli grafik bor) |
| Sozlama ✅ (2026-11-08) | Yangi kirish ekrani **«Barcha sozlamalar»** (standart; avval to'g'ridan-to'g'ri «Bron va zalog» ochilardi): 6 guruh — kartalar to'rida (≥1280 px: 3 ustun, ≥768: 2, telefon: 1), har qator — belgi + nom + qisqa izoh (`SOZLAMA_BOLIMLAR[].izoh`), bosilsa shu bo'lim formasi. Chap menyuda (va telefon menyusida) yuqorida «Barcha sozlamalar» tugmasi. Bo'lim formalari, qidiruv, «Saqlash» paneli, guruhlar va havolalar (`sozlamalar:<id>`) o'zgarmagan — qo'ng'iroqchadan to'g'ridan-to'g'ri bo'limga o'tish avvalgidek |
Har bo'limda: avval maketdagi nisbatda karta to'ri, keyin mavjud funksiyalar kartalarga joylanadi; E2E selektorlari (role/nom) saqlanadi.
