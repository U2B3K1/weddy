# Libosa Academy — metodika (2-variant)

> Manba: `LIBOSA_ACADEMY_METODIKA.odt` (Desktop). Bu variant o'sha hujjatning to'rt bo'lagini bitta rejaga
> birlashtiradi va uni loyiha kodi bilan solishtirib tuzatadi (2026-11-12, kod `1f405b7`).
> «Kodda tekshirildi» belgisi — model va sozlama darajasida ko'rilgan; ekrandagi tugma nomlari darsni
> yozishdan oldin jonli tizimda yana bir marta solishtiriladi.

---

## 1. Asl hujjatning kamchiliklari

### 1.1. Tuzilish

| Kamchilik | Nima uchun muammo | Tuzatish |
|---|---|---|
| Hujjat — to'rtta alohida suhbat javobining yig'indisi | Uchta har xil o'quv dasturi bor: 8+8 bosqich, keyin 12+24+24, oxirida «60 ni qat'iy maqsad qilmaymiz». Bajaruvchi qaysi biriga amal qilishini bilmaydi | Bitta dastur (4-bo'lim) |
| Sonlar o'zaro zid | «Jami 60 ta dars» deyilgan, shu joyning o'zida «sotuvchi yo'li 36 ta, rahbar yo'li 36 ta» | Sonlar bitta jadvalda |
| Suhbat qoldiqlari | «Quyidagi matnni agentingizga yuboring», «Siz yuborgan 39 ta ekran», «0x8007000F xatosi» — metodikaga aloqasi yo'q | Olib tashlandi |
| Muallif tizimni ko'rmagan | O'zi yozgan: kod o'qilmadi, sayt ochilmadi. Shu sababli bir necha dars mavjud bo'lmagan funksiyaga qurilgan (1.2) | Kod bilan solishtirildi |

### 1.2. Haqiqiy tizimga mos kelmaydigan joylar

| Hujjatda | Tizimda (kodda tekshirildi) | Darsga ta'siri |
|---|---|---|
| Ikki rol: sotuvchi va rahbar | **Uch rol:** rahbar, sotuvchi, kassir | Kassir uchun qisqa alohida yo'l kerak |
| U02–U05: shaxsiy parol, «parolni tiklash», «faol sessiyalar», «qo'shimcha himoyani sozlash» | Kirish boshqacha: qurilmaga **salon logini va paroli** bir marta kiritiladi → xodim o'zini tanlaydi → **PIN**. Yangi qurilma rahbar ruxsatini kutadi (salonning birinchi qurilmasi darhol ishonchli). Rahbardan Telegram orqali ikkinchi tasdiq so'raladi, 3 kun faol bo'lmasa qayta. Xato PIN'lar xodimni vaqtincha bloklaydi. Xodimda shaxsiy parol ham, «parolni tiklash» ham yo'q — PIN'ni rahbar almashtiradi | U03–U05 shu ko'rinishda yozib bo'lmaydi; o'rniga 2 ta dars: «Kirish va PIN», rahbarga «Qurilmalar va salon paroli» |
| Bildirishnomalar kabinetda sozlanadi | Xabar turlari, jamlanma, tinch vaqt, maxfiylik — **botdagi «⚙️ Sozlamalar»** da. Kabinetda faqat ulash va uzish | Dars ekrani — Telegram, kabinet emas |
| «Sinov bildirishnomasini olish» | Bunday tugma topilmadi | Mashq haqiqiy hodisa bilan tekshiriladi (masalan, o'quv salonida zakaz yaratilganda keladigan xabar) yoki tugma alohida ish sifatida qo'shiladi |
| «Garovning saqlov joyini qayd etish» | Garov turlari: **pul, hujjat, tillo buyum**. Saqlov joyi yo'q — **seyfdagi raqamli yorliq** bor. Holatlar: saqlanmoqda / qaytarildi / jarima uchun ushlab qolindi. Smena oxirida hujjat va tillo garov «joyida» deb belgilanadi | Garov darslari shu uch tur va yorliq atrofida |
| Zakaz holatlari — «tekshiriladi» | Vaqtinchalik bron → Bron → Berildi → Qaytarildi → Yopildi; alohida «Bekor qilingan». Vaqtinchalik bron standart 24 soat, libos qulfi 15 daqiqa (ikkalasi sozlanadi) | Sotuvchi yo'lining asosiy o'qi shu zanjir |
| «Alohida kassir rejimi» umumiy aytilgan | Sozlama `Kassa` bo'limida: «Sotuvchi o'zi kassir» yoki «Alohida kassir». Ikkinchisida sotuvchi pul bilan umuman ishlamaydi, menyusida kassa bo'limi qisqaradi | Variantni o'quvchi tanlamaydi — o'z salonining sozlamasidan olinadi |
| Vizual: «iliq jigarrang salon muhiti» | Mahsulot uslubi — «Shisha»: **to'q ko'k fon, oltin urg'u** | Akademiya ilovaning o'zi bilan bir xil ko'rinsin; jigarrang faqat video sahnalarda |

### 1.3. Hujjatda umuman yo'q, tizimda bor

Darslar xaritasiga qo'shilishi kerak:

- **Chegirma so'rovi** — sotuvchi so'raydi, rahbar tasdiqlaydi; «tayyor chegirma» tasdiqsiz. Ikki rolni bog'laydigan eng tabiiy voqea.
- **Sotuvchi qo'shgan libos** — rahbar tasdig'ini kutadi («Tasdiq kutilmoqda»).
- **Xarajat tasdig'i** — kutilmoqda / tasdiqlandi / rad etildi.
- **Mavsumiy narx**, **kechikish jarimasi**, **shartnoma bandlari**, **libos artikuli**.
- **Filiallar** — qurilma filialga biriktiriladi, zakaz va kassa shu filialga yoziladi; har filialda alohida kassa bo'lishi mumkin.
- **Ta'mir** va **tozalash** — tozalashdagi libos kelajakka ham bron qilinmaydi (atayin shunday).
- **To'lov usullari** — naqd, terminal, o'tkazma, Click, Payme; terminal sverkasi va o'tkazma tasdig'i.
- **Texnik yordam ruxsati** — rahbar platforma egasiga muddatli ko'rish ruxsatini beradi.
- **Obuna** — sinov davri, to'lov, muddat o'tsa «faqat ko'rish» holati; botdagi «💳 To'lov».
- **Boshlash ro'yxati** — rahbarning dashbordida tayyor turibdi; rahbar yo'lining birinchi darslari shu ro'yxat qadamlariga bog'lanadi, alohida «salonni tayyorlash» ixtiro qilinmaydi.
- **Telefon ko'rinishi** — hujjatda faqat kompyuter va planshet. Sotuvchi darsni ko'pincha telefonda ochadi.

### 1.4. Metodikaning o'zidagi bo'shliqlar

1. **Hajm real emas.** 60 dars × kirish videosi × ekran yozuvi × kassa rejimi bo'yicha ikki variant. Libosa interfeysi hozir haftasiga bir necha marta o'zgaryapti — bunday hajm bir oyda eskiradi.
2. **Eng qiyin qism — o'quv muhiti — ikki jumlada o'tilgan.** Har o'quvchiga alohida salon, darsga mos boshlang'ich holat, qayta boshlash, tashqi xabarlarni o'chirish, natijani server tekshirishi — loyihaning asosiy muhandislik ishi shu. Videolar emas.
3. **AI ustozning narxi va chegarasi yo'q.** Qaysi model, kim to'laydi, noto'g'ri javob bersa nima bo'ladi — aytilmagan. Pul bo'yicha xato maslahat salonga zarar.
4. **Qat'iy sanalar.** «20–22 noyabr» bir oydan keyin o'tgan sana bo'ladi va mashq ishlamay qoladi.
5. **«Sababini topadi» degan mashqlarning sababi yozilmagan.** Smena farqi darsida 50 000 so'm qayerdan kelgani ssenariyda yo'q — tekshiruv mezonini yozib bo'lmaydi.
6. **Rahbar xodimining o'qishini ko'rmaydi.** Ko'nikmalar pasporti bor, lekin kimga ko'rinishi aytilmagan. Rahbar uchun asosiy foyda aynan shu: yangi sotuvchi qaysi ishni mustaqil bajara oladi.
7. **Muvaffaqiyat o'lchovi yo'q.** Akademiya ishlayaptimi yoki yo'qmi — qanday bilinadi?
8. **Kichik salon holati hisobga olinmagan.** Ko'p salonda ega o'zi sotuvchi ham. Unga 24+24 dars emas, bitta qisqa yo'l kerak.
9. **Yangilanish qo'lda.** «Tugma o'zgarsa dars pasportidan ko'rinadi» — kim solishtiradi? Avtomatik bo'lmasa, bajarilmaydi.
10. **Hisobot darslari buxgalteriya tiliga og'gan** («marja», «qoplash»). Libosa egasi uchun sodda: foyda kassa usulida, soliq va buxgalteriya yo'q.

---

## 2. Asosiy qarorlar

1. **Dars — bajarilgan ish.** Video ko'rilgani hisobga olinmaydi; dars o'quv salonidagi holat to'g'ri bo'lganda yopiladi.
2. **Avval bitta voqea, keyin kengaytirish.** Birinchi chiqarilish — 10 dars (5-bo'lim). Qolganlari shu qolip ishlagandan keyin.
3. **Video kam.** Har darsga emas, har **modulga** bitta 10–20 soniyali sahna. Dars ichida personaj — harakatsiz rasm va matn pufagi. Xarajat va yangilash yuki bir necha barobar kamayadi.
4. **Ekran yozuvi qo'lda olinmaydi.** Loyihada Playwright e2e bor (`frontend/e2e`). Dars namoyishi shu skriptlar bilan yoziladi — interfeys o'zgarsa qayta ishga tushiriladi, skript yiqilsa dars «eskirgan» deb belgilanadi (1.4-ning 9-bandi shu bilan yopiladi).
5. **Tekshiruv — kod, AI emas.** Har darsning mezonini server o'quv salonining holatidan hisoblaydi. AI faqat tushuntiradi.
6. **1-versiyada AI ustoz yo'q.** Uch darajali yordam (ishora → qadam → namoyish) har qadam uchun oldindan yozilgan matn. AI — ikkinchi bosqich, o'lchangan ehtiyoj bo'lsa.
7. **Sanalar nisbiy.** «Kelasi shanba–dushanba» — o'quv salonini tayyorlashda bugungi kundan hisoblanadi.
8. **Yo'nalish haqiqiy roldan olinadi**, kassa darslari varianti — salonning `kassa_rejimi` sozlamasidan. O'quvchi hech narsa tanlamaydi.
9. **O'quv yutug'i vakolat bermaydi.** Rol va huquqlarni faqat rahbar o'zgartiradi.
10. **Jarima va hisobot sodda.** Jarima — bitta qisqa dars. Hisobotlarda buxgalteriya atamalari ishlatilmaydi.

---

## 3. O'quv muhiti (asosiy muhandislik ishi)

Libosa ko'p salonli tizim — har bir yozuv salonga bog'langan. Shu sababli o'quv muhiti alohida server emas, **o'quv belgisi qo'yilgan oddiy salon**.

| Talab | Yechim |
|---|---|
| Har o'quvchiga alohida holat | Har xodimga shaxsiy o'quv saloni (`Salon` da yangi belgi, masalan `oquv`); haqiqiy salon ma'lumotiga tegmaydi |
| Dars boshidagi holat | Har dars uchun «ssenariy urug'i» — kerakli libos, mijoz, zakaz, to'lovni yaratadigan funksiya. Namuna sifatida mavjud `demo_ezaz` buyrug'i |
| Qayta boshlash | O'quv salonini tozalab, urug'ni qayta ishga tushirish |
| Tashqi ta'sir yo'q | `oquv` salonida SMS (Eskiz), Telegram xabarlari, obuna hisobi, platforma egasiga boradigan xabarlar o'chiriladi; mijozga hech narsa ketmaydi |
| Qurilma ruxsati | Mavjud `qurilma_avto_tasdiq` belgisi — o'quv salonida yangi qurilma darhol ishonchli |
| Natijani tekshirish | Dars kodi → tekshiruv funksiyasi: o'quv saloni holatidan «bajarildi / bajarilmadi + sabab» qaytaradi |
| Hisobotlarni buzmaslik | O'quv salonlari platforma paneli statistikasi, obuna ro'yxati va zaxira hisobotlariga kirmaydi |
| Tozalash | 30 kun ochilmagan o'quv saloni o'chiriladi (cron) |

Tekshiruv mezoni namunasi — «Garovni qaytarish»: zakaz holati «Qaytarildi» yoki «Yopildi»; garov holati «Qaytarildi»; kassada bitta «Garovni qaytarish» yozuvi (ikkita emas); summa olingan garovga teng.

### 3.1. Manzil — `academy.libosa.uz` (ega qarori, 2026-11-12)

Akademiya alohida subdomenda ishlaydi. Bu «mashq qayerda bajariladi» savolini ham yopadi:

- **Subdomenning o'zi — o'quv rejimi belgisi.** `academy.libosa.uz` da ilova faqat o'quvchining o'quv saloni bilan ishlaydi; haqiqiy salon ma'lumotiga bu manzildan umuman yetib bo'lmaydi. `libosa.uz` da esa o'quv saloni ko'rinmaydi. Xodim adashmaydi: manzil boshqa, tepada doimiy «O'quv saloni» tasmasi.
- **Bitta backend, bitta baza.** Alohida server yoki alohida baza kerak emas: `academy.libosa.uz/api/` o'sha gunicorn'ga boradi. Server so'rov qaysi hostdan kelganiga qarab ishlaydi — akademiya hostidan kelgan so'rov faqat `oquv` saloniga yozadi (himoya frontendda emas, serverda).
- **Frontend.** Ilova ekranlari qayta yozilmaydi — o'sha komponentlar ishlatiladi, ustiga dars paneli (topshiriq, yordam, tekshiruv) qo'shiladi. Alohida build yoki bitta build ichida host bo'yicha rejim — 1-bosqichda hal qilinadi.
- **Kirish.** Brauzerda har manzilning xotirasi alohida (qurilma belgisi va sessiya `libosa.uz` da saqlanadi, `academy.libosa.uz` ularni ko'rmaydi). Shuning uchun:
  - Xodim `libosa.uz` dagi «Akademiya» tugmasini bosadi → server bir martalik, 1 daqiqalik havola beradi → `academy.libosa.uz` uni sessiyaga almashtiradi. Qayta login va PIN so'ralmaydi.
  - To'g'ridan-to'g'ri `academy.libosa.uz` ga kirgan odam ochiq darslarni ko'radi; davom etish uchun «Libosa orqali kirish» tugmasi.
  - K1 «Kirish va PIN» darsi o'quv salonining o'z kirish ekranida mashq qilinadi (soxta PIN bilan), haqiqiy PIN akademiyada terilmaydi.
- **Ochiq darslar.** Ro'yxatdan o'tmagan mehmon uchun vaqtinchalik o'quv saloni (24 soatdan keyin o'chadi) — birinchi 2–3 dars reklama vazifasini bajaradi, oxirida «Saloningizni ulang» so'rovi (mavjud a'zo bo'lish arizasi).
- **Serverda bir martalik ish** (ega SSH orqali bajaradi, buyruqlar `deploy/DEPLOY.md` ga yoziladi): DNS'da `academy` uchun A yozuvi; `certbot` bilan sertifikat; nginx'da yangi `server` bloki; `.env` dagi `ALLOWED_HOSTS` ga `academy.libosa.uz`. API shu hostning o'zidan `/api/` orqali berilgani uchun CORS sozlamasi kerak emas.
- **Video fayllar** nginx'dan to'g'ridan-to'g'ri beriladi (`/media/` kabi), bazaga va zaxiraga kirmaydi.

---

## 4. O'quv dasturi

Dars 3–6 daqiqa. Kod: K — kirish (hamma), S — sotuvchi, P — pul (kassa rejimiga qarab), R — rahbar.

### 4.1. Kirish — hamma uchun (4 dars)

| Kod | Dars | Tekshiriladigan natija |
|---|---|---|
| K1 | Kirish va PIN | O'z ismini tanlab PIN bilan kirdi; PIN'ni hech kimga bermaslik va xato terilsa nima bo'lishi haqidagi savolga to'g'ri javob berdi |
| K2 | Bosh sahifa va bugungi ishlar | Bugun olib ketiladigan va qaytariladigan zakazni topib ochdi |
| K3 | To'rt xil pul | Bitta zakazda ijara, avans, qoldiq va garovni to'g'ri ko'rsatdi |
| K4 | Telegramni ulash | Bir martalik kod bilan botga ulandi; botdagi «⚙️ Sozlamalar»da tinch vaqtni o'rnatdi; uzishni biladi |

### 4.2. Sotuvchi (12 dars)

| Kod | Dars | Tekshiriladigan natija |
|---|---|---|
| S1 | Mijozga libos topamiz | Sana va o'lchamga mos, bo'sh libosni tanladi (band va tozalashdagisini emas) |
| S2 | Libos kartasi va kalendar | Libosning keyingi bo'sh kunini to'g'ri aytdi |
| S3 | Mijozni topish yoki qo'shish | Mavjud mijozni topdi, takror yozuv yaratmadi |
| S4 | Birinchi zakaz | To'g'ri sana, libos va mijoz bilan zakaz yaratdi |
| S5 | Vaqtinchalik bron | Avanssiz bron qachon o'z-o'zidan bekor bo'lishini to'g'ri aytdi; avans bilan «Bron»ga o'tkazdi |
| S6 | Aksessuar qo'shish | Zakazga yaroqli aksessuar qo'shdi |
| S7 | Chegirma so'rash | Tayyor chegirmani qo'lladi; kattasiga sabab bilan so'rov yubordi |
| S8 | Libosni topshirish | Tizim so'ragan shartlarni bajarib «Berildi»ga o'tkazdi |
| S9 | Libosni qaytarib olish | Libos holatini belgiladi, zakaz «Qaytarildi» bo'ldi |
| S10 | Kechikkan zakaz | Kechikkan zakazni topdi va tizim ko'rsatgan yo'l bilan yakunladi |
| S11 | Sana yoki libosni almashtirish, bekor qilish | Almashtirgandan keyin bandlik va summa to'g'ri |
| S12 | Sanoqda qatnashish | Libosni artikul bo'yicha topib, joyini belgiladi |

### 4.3. Pul (6 dars) — kim o'tadi

«Sotuvchi o'zi kassir» rejimida — sotuvchi; «Alohida kassir» rejimida — kassir (sotuvchiga bitta dars: P0 «To'lovni kassirga yo'naltirish»). Rahbar ikkala holatda ham o'tadi.

| Kod | Dars | Tekshiriladigan natija |
|---|---|---|
| P1 | Smenani ochish | Smena ochildi, boshlang'ich naqd to'g'ri |
| P2 | Avans va qoldiqni qabul qilish | To'lov to'g'ri zakazga, to'g'ri usul bilan (naqd / terminal / o'tkazma / Click / Payme) yozildi |
| P3 | Garovni qabul qilish | Garov ijara to'lovidan alohida, to'g'ri tur va yorliq bilan yozildi |
| P4 | Garovni qaytarish | Bir marta qaytarildi, summa mos |
| P5 | Xarajat va pul topshirish | Xarajat modda va sabab bilan; topshirish qabul qiluvchiga yuborildi |
| P6 | Smenani yopish | Naqd sanaldi, terminal sverkasi kiritildi, garovlar «joyida» belgilandi |

### 4.4. Rahbar (14 dars)

| Kod | Dars | Tekshiriladigan natija |
|---|---|---|
| R1 | Boshlash ro'yxati | Dashborddagi boshlash ro'yxatining qadamlarini bajardi |
| R2 | Xodim qo'shish | Xodimni rol va PIN bilan qo'shdi; ishdan ketganni o'chirishni biladi |
| R3 | Qurilmalar va salon paroli | Yangi planshetga ruxsat berdi, begona qurilmani o'chirdi |
| R4 | Kassa tartibi | «Sotuvchi o'zi kassir» va «Alohida kassir» farqini oqibati bilan ko'rdi |
| R5 | Libos qo'shish va tasdiqlash | Libosni narx va tannarx bilan qo'shdi; sotuvchi qo'shganini tasdiqladi |
| R6 | Bron va garov qoidalari | Tozalash kunini o'zgartirib, libos bandligi qanday surilishini ko'rdi |
| R7 | Narx: mavsumiy ustama, chegirma, promokod | Chegirma so'rovini tasdiqladi yoki rad etdi |
| R8 | Avans qaytarish va kechikish | Bekor qilingan zakazda qancha qaytishini to'g'ri hisobladi |
| R9 | Smena farqini tekshiramiz | Farq sababini topdi (ssenariy: sotuvchi 50 000 so'mlik terminal to'lovini «naqd» deb yozgan) |
| R10 | Pul topshirish va xarajat tasdig'i | Topshirishni qabul qildi, xarajatni tasdiqladi |
| R11 | Sanoq | Sanoq natijasidagi yo'q libosni topdi |
| R12 | Hisobotlar | Oy tushumi va foydasini aytdi; garov nega daromad emasligini tushuntirdi |
| R13 | Bot rahbar uchun | «Bugun», «Qaror kutmoqda», «💳 To'lov»ni ishlatdi |
| R14 | Yordam va obuna | Texnik yordam ruxsatini berdi va bekor qildi; obuna muddatini topdi |

**Ega o'zi sotuvchi bo'lgan salon:** K1–K4 → S1, S4, S8, S9 → P2, P3, P4, P6 → R1, R5, R12. Jami 16 dars, taxminan bir yarim soat.

**Keyinga:** yetkazib beruvchilar, bank solishtirish, ta'mir, filiallar, shartnoma bandlari, artikul, sotuvchi bonusi, SMS, jurnal. Ularning har biri «Shu bo'limni o'rganish» tugmasi orqali ochiladigan mustaqil qisqa dars bo'ladi, yo'lga majburiy kirmaydi.

---

## 5. Birinchi chiqarilish — bitta voqea, 10 dars

Bitta zakaz ikki rolning ko'zi bilan:

> Shanba kuni to'y. Mijozga 44-o'lchamdagi milliy libos kerak. Ijara 300 000 so'm, avans 100 000, pul garovi 100 000.

| № | Dars | Kim |
|---|---|---|
| 1 | K1 Kirish va PIN | hamma |
| 2 | S1 Mijozga libos topamiz | Madina |
| 3 | S4 Birinchi zakaz | Madina |
| 4 | P2 Avans | Madina (yoki kassir) |
| 5 | P3 Garovni qabul qilish | Madina (yoki kassir) |
| 6 | S8 Libosni topshirish | Madina |
| 7 | S9 + P4 Qaytarib olish va garovni qaytarish | Madina |
| 8 | P6 Smenani yopish | Madina |
| 9 | R9 Smena farqini tekshiramiz | Nodira — aynan shu smena |
| 10 | R12 Hisobotda shu zakaz | Nodira — 300 000 tushum, 100 000 garov daromad emas |

Ichiga uchta «xatoni toping» lahzasi qo'shiladi: band libosni tanlash (2), garovni ijara to'loviga qo'shib yozish (5), sanalmagan pul bilan smenani yopish (8).

Shu 10 dars 3–5 nafar haqiqiy sotuvchi va 2–3 nafar rahbarda sinaladi. Qolgan darslar faqat shundan keyin yoziladi.

---

## 6. Dars qolipi va pasporti

| Qism | Mazmun | Hajm |
|---|---|---|
| Vaziyat | Personaj rasmi va 1–2 jumla (modul boshida — video) | 10–20 soniya |
| Natija | «Dars oxirida … qila olasiz» — bitta jumla | — |
| Namoyish | Haqiqiy ekran yozuvi, subtitr bilan, o'tkazib yuborsa bo'ladi | 30–60 soniya |
| Mashq | O'quv salonida mustaqil bajarish; topshiriq doim ko'rinib turadi | 2–4 daqiqa |
| Tekshiruv | Server holatni tekshiradi | darhol |
| Izoh | Noto'g'ri bo'lsa — aniq sabab va «Qayta urinish» | — |

Yordam: Ishora → Qadam → Namoyishni qayta ko'rsatish. Yordam bilan bajarilgan dars ham o'tgan hisoblanadi, lekin pasportda «yordam bilan» deb belgilanadi.

**Pasport** (har dars uchun bitta fayl): kod · rol · kassa rejimi varianti · sahifa · ssenariy urug'i · tekshiruv funksiyasi · e2e namoyish skripti · personaj matni · oxirgi tekshirilgan commit.

**Tayyor mezoni:** namoyish skripti joriy kodda o'tadi; mashq boshidan oxirigacha bajariladi; kamida ikkita tipik xato uchun aniq izoh bor; telefon, planshet va kompyuterda ko'rilgan.

---

## 7. Ko'nikmalar va rahbarga ko'rinishi

- Ball va reyting yo'q. Har xodimda **ko'nikmalar ro'yxati**: zakaz, to'lov, garov, topshirish, qaytarish, smena.
- Rahbar `Sozlama → Xodimlar` da har xodim yonida ko'radi: qaysi ko'nikma yopilgan, qaysi biri «yordam bilan».
- Yangi xodim qo'shilganda unga akademiyaga taklif avtomatik chiqadi (bosh sahifada va botda) — rahbar qo'lda yubormaydi.
- Yo'l tugaganda rahbarga botda bitta xabar: «Madina sotuvchi yo'lini tugatdi».
- Interfeys o'zgarganda butun kurs qayta berilmaydi — «Nima o'zgardi?» qisqa darsi chiqadi.

**Tezkor yordam:** har bo'limdagi «Shu bo'limni o'rganish» tugmasi tegishli darsni oldingi darslarni talab qilmasdan ochadi.

**Akademiya ishlayotganini qanday bilamiz:**

| O'lchov | Maqsad |
|---|---|
| Yangi xodim birinchi haftada K + asosiy 6 darsni tugatadi | 70% dan ko'p |
| Birinchi mustaqil zakazgacha vaqt | qisqaradi |
| Platforma egasiga «qanday qilinadi» savollari | kamayadi |
| Yangi xodimlarda smena farqi va garov xatolari | kamayadi |
| Dars tashlab ketilgan qadam | qaysi qadamda — shu dars qayta yoziladi |

---

## 8. Personajlar, video va vizual

- **Madina** (sotuvchi, ~28 yosh) va **Nodira** (rahbar, ~40 yosh) — asl hujjatdagi tavsif saqlanadi. Kassir yo'li uchun alohida personaj shart emas — Madina olib boradi.
- Asl hujjatdagi to'rtta Higgsfield prompti yaroqli. Qo'shimchalar:
  - Avval **salon ichki ko'rinishining** reference rasmi tasdiqlanadi — aks holda har sahnada salon boshqacha chiqadi.
  - Kadrga hech qanday yozuv, raqam va interfeys generatsiya qilinmaydi (`no text, no signage, no UI on screens`); hammasi montajda qo'shiladi.
  - Milliy liboslar generatsiyada xato chiqishi mumkin — har sahna egasi tomonidan ko'riladi; yaxshisi, reference sifatida salonning haqiqiy liboslari rasmi beriladi.
  - O'zbekcha ovoz — **VoiceLab** (`api.voicelab.uz`, model `lison`, til `uz`; kalit `VOICELAB_API_KEY` muhit o'zgaruvchisida, repozitoriyga yozilmaydi). Ega tanlagan ovoz (2026-11-12): **«Safiya — Reassuring guide»**, `voice_2785aabd-21b5-4cc7-9845-2230186ef7d9` — Nodira uchun; **«Madina — Honey»**, `voice_4ef06e6b-2229-4023-ad66-c2a7a2b736ff` — Madina uchun. Summalar matnda so'z bilan yoziladi («ellik ming»). Har holda subtitr majburiy (salonda ovoz o'chiq bo'ladi).
  - Video 720p, 20 soniyagacha, o'tkazib yuborish tugmasi bilan — mobil internetda ham ochilsin.
- **Akademiya interfeysi** — ilovaning «Shisha» uslubida (to'q ko'k fon, oltin urg'u, shisha kartalar). Iliq jigarrang–shampan palitra faqat video sahnalarda.
- **Ekranlar:** kompyuterda topshiriq chapda, ilova o'ngda; planshetda «Dars / Mashq» almashinuvi; **telefonda** topshiriq pastdan ochiladigan ixcham panel.
- Matnlar ilovadagi so'zlar bilan: «Dashboard», «Pul topshirish», «Garov», «Terminal», «Salonchi», «Sozlama».

---

## 9. Ish ketma-ketligi

| Bosqich | Natija | Ko'rsatiladi |
|---|---|---|
| 1. O'quv salon va subdomen — **qilindi (2026-11-12, PROGRESS (115))** | `oquv` belgisi, host bo'yicha cheklov, bir martalik kirish havolasi, tashqi xabarlar o'chirilgan, urug' va qayta boshlash, 2 ta tekshiruv funksiyasi; nginx namunasi | Bitta dars matnsiz, lekin `academy.libosa.uz` da ishlaydi |
| 2. Qolip — **qilindi (2026-11-12, PROGRESS (116))** | Dars ekrani (uch o'lchamda), yordam darajalari, pasport formati | S1 darsi to'liq |
| 3. Personajlar | Madina, Nodira, salon reference; bitta sinov video va ovoz | Ega tasdiqlaydi |
| 4. Birinchi voqea | 5-bo'limdagi 10 dars | Haqiqiy xodimlarda sinov |
| 5. Tuzatish | Tashlab ketilgan qadamlar qayta yoziladi | — |
| 6. Kengaytirish | 4-bo'limning qolgan darslari, ko'nikmalar rahbarga ko'rinadi | — |
| 7. AI ustoz (ixtiyoriy) | Faqat tushuntirish; dars pasporti va tekshiruv natijasiga tayanadi | Xarajat hisobi bilan |

1-bosqichda aslida nima qilindi: `backend/apps/akademiya/` (o'quv saloni, bir martalik kirish, host cheklovi, tozalash),
ikki dars tekshiruvi bilan — **S4 «Birinchi zakaz»** va **P2 «Avansni qabul qilish»**; `frontend/src/akademiya/` (kirish
sahifasi, «O'quv saloni» belgisi, oddiy darslar paneli); ilovada ism menyusida «Akademiya» tugmasi; `deploy/DEPLOY.md` §18.
Dars ekranining to'liq maketi, yordam darajalari va dars pasporti — 2-bosqich.

2-bosqichda aslida nima qilindi:

- **Dars ekrani.** Kompyuterda dars paneli chapda, ilova o'ngda ichki oynada (ilova o'z enini «ekran» deb biladi va tor
  joyda o'zi planshet ko'rinishiga o'tadi). Planshet va telefonda pastda «Dars / Mashq» almashtirgichi; mashq paytida
  tepada bir qatorli topshiriq tasmasi turadi.
- **Dars qolipi:** personaj va vaziyat → «Dars oxirida» va «Qayerda» → topshiriq → yordam → tekshiruv → keyingi dars.
- **Yordam** ikki darajali: ishora → qadamma-qadam. Uchinchi daraja (ekran yozuvi) 4-bosqichda qo'shiladi.
  Yordam bilan bajarilgan dars xaritada «yordam bilan» deb belgilanadi.
- **Dars pasporti** — har dars `backend/apps/akademiya/darslar/` dagi bitta fayl (`DARS = Dars(...)`): kod, yo'nalish,
  personaj, sahifa, vaziyat, natija, urug', topshiriq, yordam matnlari, tekshiruv va oxirgi solishtirilgan sana.
  Jadval ko'rinishida: `python manage.py dars_pasportlari`.
- **Darslar:** S1 «Mijozga libos topamiz» (javob panelda tanlanadi), S4 «Birinchi zakaz», P2 «Avansni qabul qilish» —
  uchalasi haqiqiy interfeysda boshidan oxirigacha o'tilgan, qadamlar matni ekrandagi yozuvlar bilan solishtirilgan.
- Personaj rasmi o'rnida hozircha ismning bosh harfi (rasmlar — 3-bosqich, Higgsfield krediti kerak).

**Yo'naltirilgan mashq (2026-11-12, ega talabi; PROGRESS (117)).** Erkin mashq rad etildi: o'quvchi boshqa joylarni
bosib adashadi. AGINE Academy formati o'rganildi va quyidagilar olindi:

| AGINE'da | Libosa'da |
|---|---|
| Bir ekranda bitta qadam, tepada qadam nuqtalari | Xuddi shunday: panelda faqat joriy qadam |
| Amaliyot tashqi dasturda, o'quvchi bandlarni o'zi belgilaydi | Ilova bizniki — **ekranda faqat kerakli tugma yoritiladi**, qolgani bosilmaydi; qadam bajarilganini tizim o'zi biladi |
| Qahramon darajasi va XP | Daraja (Yangi xodim → Shogird → Mustaqil xodim → Usta) va XP, faqat birinchi marta bajarilganda |
| Dars oxirida «endi o'zing, shablonsiz» topshirig'i | Tanlov qadamlari ochiq qoldirilgan (qaysi libos — o'quvchi topadi), yakunda tizim tekshiradi |
| Kino-kirish, hikoya ovozi, qahramon rasmi | Hali yo'q — 3-bosqich (rasm va video uchun Higgsfield krediti kerak; ovoz VoiceLab'da tayyor) |
| Har qadamga bog'langan AI ustoz | Hali yo'q; hozircha «Yordam» (ishora) |

### Egadan kutilayotgan qarorlar

1. ~~Mashq qayerda bajariladi?~~ — **hal qilindi (2026-11-12): `academy.libosa.uz`**, tafsilot 3.1 da.
2. **Akademiya kimga ochiq?** Faqat obunadagi salon xodimlariga yoki ro'yxatdan o'tmaganlarga ham (reklama vazifasida). Tavsiya: birinchi voqeaning 2–3 darsi ochiq, qolgani xodimlarga.
3. **Til.** Faqat o'zbekchami yoki ruscha subtitr ham kerakmi.
4. **Video byudjeti.** Modul boshiga bitta sahna (taxminan 8 ta) yetarlimi.
5. **AI ustoz** birinchi versiyadan keyin kerakmi — sinov natijasiga qarab hal qilinadi.

---

## 10. Asl hujjatdan saqlangan g'oyalar

- Darslar bo'limlar ro'yxati emas, xodimning mustaqil ishlashga o'sish yo'li.
- Ikki yo'lni bitta zakaz bog'laydi — sotuvchi o'z amalining rahbar hisobotiga ta'sirini ko'radi.
- «Xatoni toping» mashqlari.
- Sozlamalar tugma orqali emas, oqibat orqali o'rgatiladi.
- Kasb yo'li va tezkor yordam — ikki alohida kirish.
- Higgsfield faqat personaj va sahna uchun; interfeys haqiqiy ekrandan.
- Bot — yordamchi; biznes amallari kabinetda. Botdagi havola kabinetning o'z kirishini chetlab o'tmaydi.
- O'quv yutug'i tizimdagi vakolatni oshirmaydi.
