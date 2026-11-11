# Platforma egasi tizimi — TZ va ishlar ro'yxati

Sana: 2026-11-11 · Tarmoq: `Ndiz` · Tayyorladi: `claude` (Fable 5.2)
Holat: **taklif** — hali hech biri qilinmagan. Tartib va ochiq savollar bo'yicha egasining qarori kerak (6-bo'lim).

---

## 0. Maqsad va tamoyillar

Platforma egasi Libosa'ni o'nlab salonga sotadi va yuritadi. Unga uchta savolga har kuni, bir daqiqada javob kerak:

1. **Pul:** kim to'ladi, kim to'lamadi, shu oy qancha tushdi?
2. **Salonlar:** qaysi salon ishlayapti, qaysi biri tashlab ketyapti, kimga e'tibor kerak?
3. **Tizim:** sayt, bot va zaxira nusxa joyidami?

Tamoyillar:

- **Egasi qo'lda yugurmaydi.** Eslatma va xabar tegishli odamning o'ziga avtomatik boradi; egaga faqat istisnolar
  (yetib bormagan, hal bo'lmagan holatlar) ko'rsatiladi.
- **Salon ma'lumoti yopiq qoladi** (FT-22.5). Egasi salon ichidagi zakaz va pulni faqat rahbar bergan muddatli
  yordam ruxsati bilan ko'radi. Bu TZ shu qoidani o'zgartirmaydi.
- **Sodda.** Buxgalteriya, soliq hisoboti va murakkab CRM qo'shilmaydi.
- **O'ylab topilgan ma'lumot yo'q.** Rekvizit, telefon, narx — faqat egasi kiritgani ko'rsatiladi.

---

## 1. Hozir nima bor (kod o'qib tekshirilgan)

**Panel** (`frontend/src/pages/Platforma.jsx`, `backend/apps/tenants/views_platforma.py`):

| Bo'lim | Nima qila oladi |
|---|---|
| Kirish | Login va parol (IP bo'yicha tanlashdan himoya bor) |
| Salonlar | Ro'yxat, holat bo'yicha filtr, qidiruv; salon qo'shish (login, parol, rahbar, PIN, tarif, 14 kunlik sinov) |
| Salon kartasi | Bloklash/ochish, tarifni almashtirish, salon parolini tiklash, qurilmalarni tozalash, sinov/obuna sanasini qo'lda o'zgartirish, «N oyga to'lov» (sanani uzaytiradi), platformadan chiqarish va JSON arxiv, yordam ruxsati bilan ko'rish |
| Tariflar | Qo'shish, tahrirlash, yopish (narx, xodim va filial limiti) |
| So'rovlar | Bosh sahifadan kelgan arizalar: ko'rildi deb belgilash, o'chirish |
| Telegram bot | Bot tokeni, egani botga ulash |

**Bot orqali egaga** (2026-11-11 da qo'shilgan): yangi so'rov («Bog'landim» tugmasi bilan), server xatolari,
kunlik zaxira nusxa fayli, obuna eslatmalari xulosasi, menyu «Salonlar» va «Holat».

**Avtomatik ishlaydi:** sinov → faol → muddat o'tgach 7 kun ogohlantirish → «faqat ko'rish»; salon rahbariga
obuna eslatmalari (3 va 1 kun oldin, tugash kuni, ertasi, oxirgi kun); chiqqan salon 90 kundan keyin o'chiriladi.

---

## 2. Nima yetishmaydi

| № | Muammo | Misol |
|---|---|---|
| 1 | **To'lov tarixi yo'q.** «N oyga to'lov» faqat sanani suradi — summa, sana, usul hech qayerga yozilmaydi | «Oq orzu» mart oyida to'ladimi, qancha? — javob yo'q. Shu oy jami qancha tushgani ham noma'lum |
| 2 | **Umumiy ko'rinish yo'q.** Panel darhol salonlar jadvalidan boshlanadi | Bugun kimga e'tibor kerakligini bilish uchun jadvalni qatorma-qator ko'rish kerak |
| 3 | **Salon tashlab ketayotgani ko'rinmaydi.** Faqat jami zakazlar soni va oxirgi kirish bor | Salon 3 haftadan beri zakaz ochmayapti — obuna tugaganda «uzaytirmayman» deydi, egasi kech biladi |
| 4 | **Egasining amallari yozilmaydi.** Bloklash, parol tiklash, sanani o'zgartirish jurnalga tushmaydi (faqat yordam kirishi yoziladi) | Salon «meni kim blokladi, qachon?» desa — isbot yo'q |
| 5 | **Egasi kirishi faqat parol bilan.** Salon rahbarida Telegram tasdig'i bor, egasida yo'q | Parol sizib chiqsa — barcha salonlarni bloklash yoki parolini almashtirish mumkin |
| 6 | **To'lov ma'lumoti xabarlarda yo'q.** Obuna eslatmasi «uzaytiring» deydi, lekin qanday | Rahbar xabarni oladi va baribir egaga qo'ng'iroq qilib so'raydi |
| 7 | **So'rovdan salon ochish qo'lda.** Arizadagi ism, telefon, salon nomi formaga qayta teriladi | Har yangi salon uchun 5 daqiqa nusxa ko'chirish va xato xavfi |
| 8 | **Salonlarga e'lon yuborib bo'lmaydi** | «Bugun 23:00 da texnik ish» — har bir rahbarga alohida yozish kerak |
| 9 | **Tizim holati panelda yo'q.** Xatolar faqat Telegramga keladi va saqlanmaydi | Kecha nechta xato bo'ldi, takrorlanyaptimi — ko'rib bo'lmaydi |
| 10 | **Egasi parolini faqat serverda almashtirish mumkin** (`manage.py platforma_admin`) | Parolni yangilash uchun serverga SSH bilan kirish kerak |

---

## 3. Ishlar ro'yxati

Hajm: **K** — kichik (yarim kungacha), **O'** — o'rta (1–2 kun), **KT** — katta (3+ kun).
Har bir ish: backend + frontend + test. Migratsiya kerak bo'lsa belgilangan.

### 1-bosqich — Pul (eng muhimi)

| ID | Ish | Qabul mezoni | Hajm |
|---|---|---|---|
| E-01 | **Obuna to'lovlari jadvali.** Yangi model: salon, sana, summa, necha oyga, usul (naqd / o'tkazma / boshqa), izoh, kim kiritdi, to'lovdan oldingi va keyingi muddat. «To'lov» formasi summa so'raydi (standart: tarif narxi × oy) | To'lov kiritilgach muddat avvalgidek uzayadi **va** tarixda qator paydo bo'ladi. Migratsiya | O' |
| E-02 | **Salon kartasida to'lovlar tarixi** va xato kiritilgan to'lovni bekor qilish (muddat eski sanaga qaytadi, bekor qilingan qator o'chmaydi — chizilgan holda qoladi) | Bekor qilingan to'lov tushumga kirmaydi; kim va qachon bekor qilgani ko'rinadi | K |
| E-03 | **«Tushum» bo'limi.** Oylar bo'yicha tushum, shu oy kutilayotgan summa (muddati shu oyda tugaydigan salonlar × tarif narxi), muddati o'tgan salonlar ro'yxati | Raqamlar to'lovlar jadvali bilan bir xil; bo'sh oyda «to'lov yo'q» | O' |
| E-04 | **To'lov rekviziti sozlamasi.** Egasi bir marta kiritadi: aloqa telefoni va to'lov yo'riqnomasi (erkin matn). Obuna eslatmasi va ilovadagi ogohlantirish shu matnni ko'rsatadi | Matn bo'sh bo'lsa xabarlar hozirgidek qoladi. Migratsiya | K |
| E-05 | **To'lov tasdig'i rahbarga.** To'lov kiritilgach salon rahbariga Telegram xabar: «Obuna falon sanagacha uzaytirildi, summa …» | Xabar bir marta boradi; to'lov bekor qilinsa — alohida xabar | K |

### 2-bosqich — Bosh sahifa va salon faolligi

| ID | Ish | Qabul mezoni | Hajm |
|---|---|---|---|
| E-06 | **Bosh sahifa.** Tepada raqamlar: salonlar holat bo'yicha, shu oy tushum, yangi so'rovlar. Ostida **«Diqqat» ro'yxati**: muddati 7 kunda tugaydi, muddati o'tgan, 14 kundan beri kirmagan, rahbari Telegramga ulanmagan | Har qator bosilsa salon kartasi ochiladi; hammasi joyida bo'lsa «e'tibor talab qiladigan salon yo'q» | O' |
| E-07 | **Faollik ko'rsatkichi.** Salonlar jadvalida: so'nggi 30 kundagi zakazlar soni, limitdan foydalanish (xodim 4/5, filial 1/1), «faol emas» filtri | Faqat sonlar — mijoz, summa va zakaz mazmuni ko'rinmaydi (FT-22.5) | K |
| E-08 | **Sinovdagi salonlar ko'rinishi.** Sinov tugashiga necha kun qoldi va salon shu vaqtda nechta zakaz ochdi | Egasi qaysi sinov salon «jonli» ekanini bir qarashda ko'radi | K |
| E-09 | **Faolligi tushgan salon haqida egaga xabar.** 14 kun zakaz ochmagan faol salon — haftada bir marta, bitta xulosa | Har salon haqida 30 kunda ko'pi bilan bir marta; bezovta qiluvchi takror yo'q | K |

### 3-bosqich — Salon bilan ishlash

| ID | Ish | Qabul mezoni | Hajm |
|---|---|---|---|
| E-10 | **So'rovdan salon ochish.** Arizada «Salon ochish» tugmasi — forma ism, telefon va salon nomi bilan to'lib ochiladi. Ariza holatlari: yangi / bog'lanildi / ulandi / rad etildi | Salon ochilgach ariza «ulandi» bo'ladi va salonga bog'lanadi. Migratsiya | O' |
| E-11 | **Kirish ma'lumotini tayyor matn qilib berish.** Salon yaratilgach: sayt manzili, login, parol, rahbar PIN i, botga ulanish qadamlari — bitta «nusxalash» tugmasi bilan | Matn faqat yaratilgan paytda bir marta ko'rsatiladi (parol keyin ko'rinmaydi) | K |
| E-12 | **Salon kartasida izohlar.** Sana va matn: kim bilan gaplashildi, nima kelishildi | Izohlar faqat egaga ko'rinadi. Migratsiya | K |
| E-13 | **Hammaga e'lon.** Matn yoziladi → barcha (yoki tanlangan holatdagi) salon rahbarlariga Telegram xabar va ilovada yopiladigan banner | Yuborishdan oldin «N ta salonga boradi» tasdig'i; yuborilgan e'lonlar tarixi. Migratsiya | O' |
| E-14 | **Rahbar kirishini tiklash.** Rahbar PIN ini unutgan yoki Telegramini yo'qotgan bo'lsa: PIN ni tiklash va Telegram bog'lanishini uzish | Amal jurnalga yoziladi va salon rahbariga xabar boradi | K |

### 4-bosqich — Xavfsizlik va nazorat

| ID | Ish | Qabul mezoni | Hajm |
|---|---|---|---|
| E-15 | **Egasi kirishida Telegram tasdig'i.** Salon rahbaridagi tayyor mexanizm: parol → botda «Ruxsat berish» | Bot ulanmagan bo'lsa faqat parol bilan kiriladi va panelda ogohlantirish turadi | O' |
| E-16 | **Platforma jurnali.** Egasining har bir amali yoziladi: salon ochish, bloklash, parol tiklash, sana va tarif o'zgarishi, to'lov, chiqarish. Panelda «Jurnal» bo'limi | Yozuv o'chirilmaydi va tahrirlanmaydi; salon bo'yicha filtr. Migratsiya | O' |
| E-17 | **Parolni paneldan almashtirish** (eski parol so'raladi) | Almashtirilgach boshqa qurilmalardagi sessiyalar yopiladi | K |
| E-18 | **Bloklashda sabab.** Bloklash sababi yoziladi va salon kirish ekranida ko'rsatiladi | Sabab bo'sh qoldirilsa kirish ekrani hozirgidek qoladi. Migratsiya | K |

### 5-bosqich — Tizim holati

| ID | Ish | Qabul mezoni | Hajm |
|---|---|---|---|
| E-19 | **Xatolarni saqlash.** Server xatolari bazaga yoziladi (oxirgi 30 kun): vaqt, manzil, xato turi, kod qatori, takror soni. So'rov mazmuni yozilmaydi | Telegram xabari avvalgidek ishlaydi; panelda ro'yxat. Migratsiya | O' |
| E-20 | **«Tizim» bo'limi.** Oxirgi zaxira nusxa vaqti, bot oxirgi marta qachon ishlagani, rejalashtirilgan ishlar oxirgi marta qachon bajarilgani, yuborilmay qolgan Telegram va SMS xabarlar soni | Biror ko'rsatkich eskirgan bo'lsa qizil belgi va egaga Telegram xabar | O' |
| E-21 | **Tashqi kuzatuv.** Sayt yotsa xabar beradigan tashqi xizmatni ulash bo'yicha yo'riqnoma (`/api/sogliq/` tayyor) | Kod emas — `DEPLOY.md` ga qadamlar; qaysi xizmatni tanlash egasidan | K |
| E-22 | **Zaxirani bulutga yuborish.** `zaxira.sh` dagi tayyor qatorni yoqish va rclone sozlash yo'riqnomasi | Telegramga sig'maydigan rasmlar (media) ham nusxalanadi | K |

### Keyingi (hozir rejalashtirilmaydi)

| ID | Ish | Nega keyin |
|---|---|---|
| E-23 | Onlayn to'lov: salon obunani Click/Payme orqali o'zi to'laydi, muddat avtomatik uzayadi | To'lov tizimi bilan shartnoma va sinov muhiti kerak |
| E-24 | Salon o'zi ro'yxatdan o'tadi (ariza emas, darhol sinov) | Avval qo'lda ulash jarayoni sinab ko'rilsin |
| E-25 | Yordamchi admin (faqat so'rovlar va ko'rish huquqi bilan) | Hozircha egasi bitta |
| E-26 | Salonlar va to'lovlarni Excel'ga chiqarish | Salon soni ko'payganda kerak bo'ladi |

---

## 4. Qilinmaydi

- Egasi salon zakazlari, mijozlari va pulini yordam ruxsatisiz ko'rmaydi.
- Soliq, hisob-faktura va buxgalteriya hisoboti.
- Salon nomidan zakaz ochish yoki to'lov kiritish.
- Salon xodimlarini kuzatish (kim necha soat ishladi va h.k.).

---

## 5. Ochiq savollar (egasining qarori kerak)

1. **To'lov qanday qabul qilinadi?** Naqd, kartaga o'tkazma, hisob raqam? E-04 matni va E-01 dagi «usul» ro'yxati
   shunga bog'liq.
2. **Tarifdan farq qiladigan narx bo'ladimi?** Masalan, tanish salonga chegirma. Bo'lsa — to'lov summasi tarifdan
   mustaqil kiritiladi (E-01 shunga tayyor), «kutilayotgan tushum» esa taxminiy bo'ladi.
3. **Sinov muddati hamma uchun 14 kunmi?** Hozir kodda qat'iy; salon ochishda o'zgartirish mumkin bo'lsinmi?
4. **Muddat o'tgach nima bo'lsin?** Hozir: 7 kun ogohlantirish → «faqat ko'rish» (avtomatik), bloklash esa qo'lda.
   Shu tartib qoladimi?
5. **E'lon (E-13) kimlarga boradi?** Faqat rahbarlargami yoki barcha xodimlargami?

---

## 6. Tavsiya etilgan tartib

1. **1-bosqich (pul)** — eng katta bo'shliq: hozir to'lov tarixi umuman yo'q. E-01 → E-02 → E-04 → E-05 → E-03.
2. **4-bosqichdan E-15 va E-16** — birinchi haqiqiy salonlar ulanishidan oldin: egasi kirishi va amallar jurnali.
3. **2-bosqich (bosh sahifa)** — salonlar 5–10 tadan oshganda zarur bo'ladi.
4. **3-bosqich** — E-10 va E-11 har yangi salonda vaqt tejaydi; qolganlari ehtiyojga qarab.
5. **5-bosqich** — E-21 va E-22 server ishi, istalgan paytda; E-19 va E-20 keyin.

Jami: 22 ta ish (K — 13, O' — 9). Muddat taxminiy: bitta agent uchun 2–3 hafta. Har bosqich oxirida ko'rinadigan natija
ko'rsatiladi va to'liq test bir marta o'tkaziladi.
