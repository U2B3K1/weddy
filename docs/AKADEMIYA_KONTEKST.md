# Libosa va Libosa Academy — boshqa agent uchun kontekst

> Bu matn mustaqil: uni o'qigan agent loyihani ko'rmagan deb hisoblanadi. Maqsad — **o'quv darsligi (akademiya)
> bo'yicha ikkinchi fikr olish**. Oxirida aniq savollar bor. Holat: 2026-11-13.
> «Kodda tekshirilgan» deyilmagan joylar — reja yoki taxmin.

---

## 1. Libosa nima

Libosa — to'y liboslarini **ijaraga beradigan salonlar** uchun veb-tizim (O'zbekiston, interfeys o'zbek tilida).
Ko'p salonli: har salon o'z ma'lumotini ko'radi, platforma egasi bitta. Jonli manzil — `libosa.uz`.
Texnologiya: Django + DRF (backend), React (frontend), bitta umumiy Telegram bot.

Foydalanuvchilar — texnik bo'lmagan odamlar: sotuvchi qizlar, kassir, salon egasi. Asosiy qurilma — planshet va telefon.

### 1.1. Rollar (kodda tekshirilgan)

| Rol | Nima qiladi |
|---|---|
| **Rahbar** (salon egasi) | Hamma narsa: sozlamalar, xodimlar, narxlar, tasdiqlar, hisobotlar |
| **Sotuvchi** | Zakaz oladi, libos beradi va qaytarib oladi; pul bilan ishlashi salon sozlamasiga bog'liq |
| **Kassir** | Faqat pul: to'lov qabul qiladi, smena yuritadi |

Kassa tartibi salon sozlamasi: **«Sotuvchi o'zi kassir»** (har sotuvchi pul oladi) yoki **«Alohida kassir»**
(sotuvchi pulga tegmaydi).

### 1.2. Kirish (kodda tekshirilgan)

Shaxsiy login-parol yo'q. Qurilmaga bir marta **salon logini va paroli** kiritiladi → xodim ro'yxatdan o'zini tanlaydi →
**PIN**. Yangi qurilma rahbar ruxsatini kutadi. Rahbar kirishi Telegram orqali qo'shimcha tasdiqlanadi.
10 daqiqa harakatsizlikdan keyin xodim avtomatik chiqadi.

### 1.3. Asosiy jarayon — zakaz

Zakaz **uch qadamda** yaratiladi, tartib qat'iy:

1. **Sana** — olib ketish va qaytarish kuni.
2. **Libos** — tizim faqat shu kunlarga bo'sh liboslarni ko'rsatadi; «Qo'shish» bosilganda libos shu sotuvchi uchun
   vaqtincha (15 daqiqa) qulflanadi.
3. **Mijoz** — telefon va ism. **Mijoz ma'lumotisiz zakaz saqlanmaydi.**

Zakaz holatlari: **Vaqtinchalik bron** (avans yo'q, standart 24 soatdan keyin o'zi bekor bo'ladi) → **Bron** (avans
olingan) → **Berildi** → **Qaytarildi** → **Yopildi**; alohida — **Bekor qilingan**.

Bandlik: libos olib ketish kunidan qaytarish kunigacha va undan keyin tozalash uchun yana bir necha kun band.
Tozalash yoki ta'mirdagi libos umuman bron qilinmaydi.

### 1.4. Pul

- **Ijara haqi** = avans + qoldiq. Avans bronni tasdiqlaydi; qoldiq odatda libos topshirilganda olinadi.
- **Garov** — alohida, qaytariladigan: pul, hujjat yoki tillo buyum. Libos berilayotganda olinadi, qaytganda
  qaytariladi (yoki jarima uchun ushlab qolinadi). Garov daromad emas.
- To'lov usullari: naqd, terminal, o'tkazma.
- **Smena**: ochiladi (seyfdagi naqd sanaladi) → kun davomida to'lovlar → yopiladi (naqd sanaladi, tizim bilan
  solishtiriladi, farq chiqsa rahbar ko'radi). Xodimlar bir-biriga va rahbarga pul topshiradi.
- Xarajatlar rahbar tasdig'i bilan.

### 1.5. Boshqa bo'limlar

Liboslar katalogi va aksessuarlar, sanoq (inventarizatsiya), mijozlar va «salonchilar» (mijoz olib keladigan
hamkorlar), chegirmalar (sotuvchi so'raydi — rahbar tasdiqlaydi), promokodlar, mavsumiy narx, kechikish jarimasi,
filiallar, hisobotlar, Telegram bot (eslatmalar, tasdiqlar, kunlik hisobot), SMS eslatmalar.

### 1.6. Egasining tamoyillari

- Sodda va egaga yo'naltirilgan: buxgalteriya va soliq yo'q, foyda kassa usulida.
- Jarima atrofida qo'shimcha nazorat qo'shilmaydi.
- Eslatmalar tegishli odamning o'ziga avtomatik boradi; platforma egasiga qo'l ishi qolmasligi kerak.
- Ko'rinish: «Shisha» uslubi — to'q ko'k fon, oltin urg'u.

---

## 2. Libosa Academy

### 2.1. Maqsad

Yangi xodim tizimdan **mustaqil** foydalana olishi, platforma egasi esa har salonni qo'lda o'rgatmasligi.
Video ko'rilgani hisobga olinmaydi — dars amaliy topshiriq bajarilganda yopiladi.

### 2.2. Egasi nimani xohlaydi

Namuna — **AGINE Academy** (`academy.agineai.com`, Claude'ni o'rgatadigan o'yin-kurs). Egasining so'zlari:
«shu format qiziq, esda qolarli, zerikarli emas, yaxshi ish beradi».

AGINE'da ko'rilgan narsalar (bepul darslari o'tib chiqilgan):

- to'liq ekranli kino-kirish, hikoya ichida qahramon nomidan tanlov;
- bir ekranda bitta qadam, tepada qadam nuqtalari;
- qadam turlari: tanlov (yo'l shunga qarab o'zgaradi), nazariya, tamoyil (qisqa eslatma + ekran yozuvi), amaliyot;
- amaliyot mayda bandlarga bo'lingan, har birida aniq tugma nomi; hamma band belgilanmaguncha «Davom» ochilmaydi;
- qahramonning darajasi va XP, yo'l xaritasida bo'limlar «qahramon egallaydigan qobiliyat» nomi bilan;
- dars oxirida «endi shablonsiz, o'zing bajar» va «hozir nima sodir bo'ldi» xulosasi;
- har qadamga bog'langan AI ustoz (faqat shu qadam mavzusida javob beradi).

Muhim farq: AGINE'da amaliyot **tashqi dasturda** bajariladi va o'quvchi bandlarni o'zi belgilaydi.
Libosa'da ilova o'zimizniki — qadam bajarilganini tizim o'zi aniqlay oladi.

### 2.3. Egasi rad etgan narsa

Birinchi variantda dars paneli yonida butun ilova erkin ochiq edi. Egasi: «bu bo'lmaydi, mashqni bajargunicha boshqa
joylarni ham bosib tashlaydi». Shundan keyin mashq **yo'naltirilgan** qilindi (2.5).

Yana ikki e'tiroz va javoblari:

- «O'quv mashg'ulotidamanmi yoki haqiqiy profildamanmi, tushunmayapman» → doimiy oltin «O'QUV SALONI» tasmasi;
  dars bo'lmagan paytda ilova ustidan parda tushadi.
- «Bir darsda mijoz kiritish bor, boshqasida yo'q — yolg'on ko'nikma berishi mumkin» → har dars oxirida xulosa:
  nima qilindi va haqiqiy ishda keyin nima keladi.

### 2.4. Qabul qilingan qarorlar

1. Manzil — `academy.libosa.uz`. O'sha backend va baza; server so'rov qaysi manzildan kelganiga qarab ajratadi.
2. Har o'quvchiga **shaxsiy o'quv saloni** (soxta mijozlar, liboslar, pullar). Haqiqiy salonga tegmaydi, undan SMS
   va Telegram xabari chiqmaydi. Roli va kassa tartibi o'quvchining haqiqiy salonidan olinadi.
3. Kirish: haqiqiy ilovadagi «Akademiya» tugmasi → bir martalik havola → parolsiz o'tadi.
4. Tekshiruv — **kod**, AI emas: server o'quv salonining holatiga qarab «bajarildi / bajarilmadi + sabab» deydi.
5. Birinchi versiyada AI ustoz yo'q; yordam oldindan yozilgan (ishora).
6. Video kam: har darsga emas, har bo'limga bitta qisqa sahna.
7. Sanalar nisbiy («kelasi shanba»), dars eskirmasligi uchun.
8. Ikki personaj: **Madina** (sotuvchi, ~28 yosh) sotuvchi yo'lini, **Nodira** (rahbar, ~40 yosh) rahbar yo'lini olib boradi.
9. O'zbekcha ovoz — VoiceLab xizmati, ovozlar tanlangan. Personaj rasmlari va video — Higgsfield (hali qilinmagan).
10. O'quv yutug'i tizimdagi vakolatni oshirmaydi.

### 2.5. Hozir ishlayotgan dars formati (qurilgan va brauzerda sinalgan)

Ekran: kompyuterda chapda dars paneli, o'ngda ilova (ichki oynada); planshet va telefonda pastda «Dars / Mashq»
almashtirgichi, mashq paytida tepada joriy qadam matni.

Dars uch bosqichdan iborat:

1. **Hikoya.** Personaj vaziyatni aytadi (1–2 jumla), «Dars oxirida …» va mukofot (XP). «Boshlash».
2. **Yo'naltirilgan mashq.** Panelda bitta qadam («3-qadam / 10» va ko'rsatma). Ilovada **faqat shu qadamning
   tugmasi yoritiladi, qolgan joy xiralashadi va bosilmaydi**. Qadam bajarilsa, o'zi keyingisiga o'tadi.
   - Tanlov kerak joyda maydon ochiq qoladi: masalan, liboslar ro'yxati to'liq yoritiladi, qaysi libosni qo'shish —
     o'quvchi o'zi topadi.
   - O'quvchi adashsa yoki sahifa yangilansa, yoritgich uni kerakli joyga qaytaradi.
3. **Yakun.** Oxirgi qadamdan keyin tizim o'zi tekshiradi: mezonlar ro'yxati (✓ / ✕ sababi bilan), XP, daraja,
   xulosa, «Keyingi dars».

Daraja: Yangi xodim → Shogird (100 XP) → Mustaqil xodim (250) → Usta (500). XP faqat birinchi marta bajarilganda.
Dars bo'lmagan paytda ilova yopiq — erkin kezish yo'q.

### 2.6. Yozilgan darslar (3 ta)

| № | Dars | Qadamlar | Tekshiruv |
|---|---|---|---|
| 1 | **Libos bo'shmi?** — mijoz hali zakaz bermayapti, faqat so'rayapti | Kassa → Yangi zakaz → 2 sana → liboslar ro'yxati (faqat ko'rish) → panelda savol: «qaysi libosni taklif qilasiz?» | Tanlangan variant; har noto'g'ri javobga o'z sababi (band / o'lchami boshqa) |
| 2 | **Birinchi zakaz** | Kassa → Yangi zakaz → 2 sana → libosni qo'shish (tanlov ochiq) → telefon → ism → saqlash (10 qadam) | Zakaz bormi, sanalar, to'g'ri libos, ism yozilganmi |
| 3 | **Avansni qabul qilish** (faqat pul bilan ishlaydiganlarga) | Kassa → To'lov qabul → zakazni tanlash → summani tuzatish (standart — to'liq narx) → Naqd → qabul qilish | Summa, usul, bron tasdiqlanganmi; pul boshqa zakazga yozilgan bo'lsa aytadi |

Har darsda bitta «tuzoq» bor: 1-da mos o'lchamdagi libos band, 2-da bo'sh lekin boshqa o'lchamdagi libos,
3-da summa maydoni to'liq narx bilan to'lib turadi.

### 2.7. Rejadagi darslar (hali yozilmagan)

Jami taxminan 36 dars: tanishuv (kirish va PIN, bosh sahifa, to'rt xil pul, Telegram), sotuvchi (libos kartasi,
mijoz, vaqtinchalik bron, aksessuar, chegirma so'rash, topshirish, qaytarib olish, kechikish, almashtirish va bekor
qilish, sanoq), pul (smena ochish, garov olish va qaytarish, xarajat va pul topshirish, smena yopish), rahbar
(xodim qo'shish, qurilmalar, kassa tartibi, libos qo'shish, bron qoidalari, narx va chegirma, smena farqi,
sanoq, hisobotlar, bot).

Birinchi chiqarilish — bitta zakaz atrofidagi voqea: zakaz → avans → garov → topshirish → qaytarish → smena yopish
→ rahbar shu smenani tekshiradi → hisobotda shu zakaz.

### 2.8. Ma'lum kamchiliklar

- Personaj rasmi yo'q (bosh harf turibdi), kino-kirish va ovoz darsga ulanmagan.
- Ekran yozuvi (namoyish) yo'q.
- 1- va 2-dars bir xil besh qadam bilan boshlanadi (Kassa → Yangi zakaz → sanalar).
- O'quv salonidagi liboslar rasmsiz.
- Haqiqiy xodimlarda hali sinalmagan — faqat ishlab chiquvchi va egasi ko'rgan.
- Rahbar xodimining qaysi darslarni o'tganini hali ko'rmaydi.

---

## 3. Sizdan so'raladigan fikr

Iltimos, quyidagilarga aniq javob bering; rozi bo'lmasangiz — nima uchun va o'rniga nima taklif qilasiz.

1. **Yo'naltirish darajasi.** Hozir deyarli har bosish yoritilgan. Bu texnik bo'lmagan xodim uchun to'g'rimi yoki
   «qo'lidan yetaklab yurish» ko'nikma bermaydimi? Qaysi nuqtada yo'naltirishni kamaytirish kerak (masalan, darsni
   ikkinchi marta yo'naltirishsiz o'tish)?
2. **Yolg'on ko'nikma xavfi.** Dars jarayonning bir qismini o'rgatsa (1-dars — faqat bandlikni tekshirish), yakundagi
   matnli xulosa yetarlimi? Yoki har dars doim to'liq jarayonni o'z ichiga olishi kerakmi?
3. **Darslar tartibi.** Yangi sotuvchining birinchi ish kunida eng kerakli 5–6 dars qaysilar va qaysi tartibda?
   Hozirgi boshlanish (bandlik → zakaz → avans) to'g'rimi?
4. **Takrorlanish.** Ko'p darslar bir xil qadamlar bilan boshlanadi. Buni qanday hal qilgan ma'qul: tayyor holatdan
   boshlash (zakaz allaqachon yaratilgan), qisqartirilgan yo'naltirish yoki shunday qoldirishmi?
5. **Xatolardan o'rganish.** Hozir tuzoqlar bor, lekin noto'g'ri tanlov faqat dars oxirida aniqlanadi va dars
   boshidan qayta boshlanadi. Xatoni o'sha zahoti ko'rsatish kerakmi yoki oxirida ko'rsatish yaxshiroqmi?
6. **O'yin unsurlari.** XP va to'rt daraja salon xodimi uchun ishlaydimi yoki ortiqchami? AGINE'dan yana nimani
   olish kerak (hikoya ichidagi tanlov, qahramonning o'sishi, kino-kirish), nimani olmaslik kerak?
7. **Rahbar yo'li.** Rahbar darslari (sozlamalar, nazorat, hisobotlar) uchun ham shu «tugmani yoritish» formati
   mosmi, yoki rahbarga boshqa format kerak (masalan, «muammoni top» turidagi topshiriqlar)?
8. **Rahbarga ko'rinishi.** Rahbar xodimining o'qishi haqida nimani ko'rishi kerak, nimani ko'rmasligi kerak
   (xodim o'zini nazorat ostida his qilib, o'qishdan qochmasligi uchun)?
9. **Nimani umuman noto'g'ri qilyapmiz?** Shu yondashuvda ko'zga tashlanadigan eng katta xato yoki ko'r nuqta nima?
