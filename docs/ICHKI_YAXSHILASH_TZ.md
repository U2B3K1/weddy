# TZ — Ichki qismni (logindan keyingi panel) mukammallashtirish

> Kim uchun: shu ishni davom ettiradigan har qanday agent (`claude`, `fcc-claude`, `antigravity`) yoki dasturchi.
> Muallif: `claude` (koordinator), 2026-11-07. Holat va turlar — pastdagi «Holat» bo'limida.
> Topilmalarning to'liq dalillari (surat, fayl:qator): `C:\Users\user\.claude\projects\F--Project-Antigravity-weddy\ichki-yaxshilash\audit\A_R1.md` va `B_R1.md`.
> Jamoa tartibi, rollar, muhit: o'sha papkadagi `JAMOA.md`.

## 0. Maqsad va tamoyillar
Logindan keyingi qism (rahbar va sotuvchi paneli) — kunlik ishni tezlashtirish, xatolarni yo'qotish, ko'rinishni bir xillashtirish.
1. **Egasi uchun sodda.** Salon egasining 3 savoli ustun: «qancha ishladim», «kassada kamomad bormi», «xodim aldamayaptimi».
   Buxgalteriya atamalari asosiy ekranga chiqmaydi. Soliq yo'q. **Rasmiy «Tushum» — faqat Foyda va zarardagi kassa usuli raqami** (`reports.foyda()`).
2. **Jarima kam ishlatiladi** — uning atrofida yangi nazorat qo'shilmaydi.
3. Mavjud uslub (tungi shisha, tilla, serif `Forum`, matn `Spectral`, kursiv `Cormorant`, `.varaq`, `.jadval-panel`) saqlanadi. Yangi palitra yo'q.
4. Har o'zgarish 390px telefon va 1440px keng ekranda tekshiriladi; telefonda sahifa gorizontal surilmasin.
5. Qaytarib bo'lmaydigan amal — faqat `Tasdiq` oynasi bilan. Xato — amal yonida, oyna ichida.
6. Commit — faqat foydalanuvchi so'raganda.

## 1. Muhit (qayta tiklash)
- Kod: `F:\Project_Antigravity\weddy` (Django+DRF `backend/`, React+Vite `frontend/`). PostgreSQL Docker, port 5433 (`docker compose up -d db`).
- **Ko'rik bazasi** `weddy_korik` (foydalanuvchining `weddy` dev bazasiga tegilmaydi). Qayta yaratish:
  ```bash
  docker exec weddy-db-1 createdb -U weddy weddy_korik
  cd backend && export DATABASE_URL=postgres://weddy:weddy@localhost:5433/weddy_korik DEBUG=True
  .venv/Scripts/python manage.py migrate
  .venv/Scripts/python manage.py shell -c "exec(open(r'<vositalar>\korik_seed.py', encoding='utf-8').read())"
  .venv/Scripts/python manage.py runserver 127.0.0.1:8002      # CORS_ALLOWED_ORIGINS=http://127.0.0.1:5175
  cd ../frontend && VITE_API_URL=http://127.0.0.1:8002/api npx vite --host 127.0.0.1 --port 5175
  ```
  `<vositalar>` = `C:\Users\user\.claude\projects\F--Project-Antigravity-weddy\ichki-yaxshilash\vositalar\`. Seed 50 kunlik ishni
  taqlid qiladi (vaqtni surib): salon `korik`/`korik123`, PIN Nodira 1111 (rahbar), Malika 2222, Dilnoza 3333, Sevara 4444.
- Skrinshot turi: `node <vositalar>\tur.mjs <papka> rahbar|sotuvchi [regex]` — har bo'lim 1440/390, xatolar `_royxat.json` da.
- Tekshiruvlar: `npm run lint`, `npm run build`, `npm run e2e` (2026-11-08: 38 test, ~6 daq, o'z serverlarini 8001/5174 da yoqadi),
  backend `manage.py test apps.<ilova>` (parallel ishlatilsa — har jarayon o'z `DATABASE_URL` nomi bilan, `JAMOA.md` 9-band).
  To'liq backend (918 test) 7,7 GB RAM da ~18 daq; yarim tundan o'tib ketsa `test_testlarda_bugun_sobit` yolg'on yiqiladi — qayta yurit.
- Bazaviy holat (2026-11-07, o'zgarishlardan oldin): E2E 23/23, build OK, lint — faqat eski ogohlantirishlar.

## 2. Fayl egaligi (parallel ishlash uchun)
| Guruh | Frontend | Backend | CSS |
|---|---|---|---|
| **D1 «Zakaz»** | `App.jsx`, `pages/{BoshEkran,Dashbord,Zakazlar,Kalendar}.jsx`, `components/{UstkiPanel,Shapka,Varaq,TolovTanlov(yangi)}.jsx`, `api/index.js` (faqat yangi funksiya qo'shish) | `apps/orders`, `apps/bookings` | `src/r1-d1.css` |
| **D2 «Boshqaruv»** | `pages/{Katalog,AksessuarBolimi,LibosSanogi,YetkazibBeruvchilar,Mijozlar,Salonchilar,Promokodlar,Hisobotlar,Sozlamalar,sozlamaBolimlari}.js(x)`, `components/{Xarajatlar,OylikGrafik,RasmBlok,TamirBlok,MavsumiyNarx,TayyorChegirmalar,Integratsiyalar,Jurnal,Oyna,OyTanlash(yangi)}.jsx` | `apps/catalog`, `apps/finance` | `src/r1-d2.css` |
| **D3 «Kassa»** | `pages/{Kassa,YangiZakaz}.jsx`, `components/{XodimMenyu,SmenaTugma,SummaInput}.jsx` | `apps/cash` | `src/r1-d3.css` |
`api/index.js` ga har guruh faqat **yangi** funksiya qo'shadi (mavjudini o'zgartirmaydi). `ichki.css`, `index.css` ga R1 da tegilmaydi.
`tenants/models.py`, `tenants/views.py`, `notify/*` — begona commit qilinmagan o'zgarishlar bor, tegilmaydi.

## 3. 1-tur (R1) vazifalari
Belgilar: [K] kritik, [Y] yuqori, [O] o'rta, [P] past. ID — audit faylidagi topilma (to'liq dalil o'sha yerda).
Har band uchun «Qabul» — QA shuni tekshiradi.

### D1 «Zakaz» — Dashboard, Zakazlar, App, backend orders/bookings
**API shartnomalari (D3 va D2 shularga tayanadi — birinchi navbatda qil):**
- `GET /api/zakazlar/royxat/?holat=tolov_kutmoqda&q=` → massiv (eski element formati), **kesimsiz**: holat `vaqtinchalik` yoki `bron`,
  va (`jami − tolangan > 0` yoki `vaqtinchalik` va `jami = 0`); tartib `olib_ketish`, `raqam`. (D3 Kassa → To'lov qabul shuni ishlatadi.)
- `GET /api/zakazlar/royxat/?...&sahifa=1&limit=50&offset=0` → `{ "natija": [...], "jami": N }`. `sahifa` berilmasa eski massiv javob
  (orqaga moslik), lekin kesim 100 → 200. Standart tab uchun yangi kalit `holat=faol` (vaqtinchalik, chegirma_kutilmoqda, bron, berildi).
- `Mijoz.manba` ga `telegram` varianti (+migratsiya). `GET /api/mijozlar/` javobida `jami` (D2 «200 tadan ko'p» xabari uchun):
  `?sahifa=1&limit=&offset=` → `{natija, jami}`; `sahifa` siz — eski massiv. Tartib: oxirgi zakaz sanasi bo'yicha.

| ID | Vazifa | Qabul |
|---|---|---|
| A-01 [K] | Qidiruv: q faqat raqam va ≤5 xona → aniq `raqam=q` birinchi qatorda; telefon bo'yicha faqat 4+ raqamda. `ZakazSonlariView` ham shu qoida | «98» → #98 birinchi; «9» → #9 chiqadi |
| A-02 [K] | Ro'yxatga sahifalash (yuqoridagi shartnoma), pastda «Yana 50 ta · 100 / 119 ko'rsatildi»; standart tab «Faol», «Hammasi» oxirida | 120 zakazning hammasiga yetib boriladi |
| A-06 [Y] | `.tezkor-tablar` faol tab: tilla matn + 2px tilla pastki chiziq; hover faqat fon (`--yuza-2`) — barcha tezkor tablar | Faol tab hoverdan aniq farq qiladi |
| A-07 [Y] + B-40(tab qismi) | Telefonda `.tezkor-tablar` o'ralsin (`flex-wrap`) yoki o'ng chetda soya; «Bugungi ishlar»da soni 0 tablar telefonda yashirin | 390px da hamma tab ko'rinadi |
| A-08 [Y] | Rahbar Dashboard tartibi: boshlash → kun varaqasi → **Bugungi ishlar** → grafiklar | 1440 da «Bugungi ishlar» birinchi ekranda |
| A-09 [Y] | Qo'ng'iroqcha: kechikkan → Zakazlar `kechikkan` filtri; chegirma → Dashboard «Qaroringiz kerak» tabi + scroll | Bosilganda aynan o'sha ro'yxat |
| A-10 [Y] | «Bugun olib ketadi» bitta ta'rif (`BUGUN_FILTRLARI['bugun_olib']`) bosh ekran va dashbordda | Sonlar hamma joyda bir xil |
| A-11 [Y] | Bosh ekran jadvalida «Qoldiq» ustuni (0 bo'lsa «To'langan») | #79 da 1 300 000 qoldiq ko'rinadi |
| A-12 [Y] | Zakaz kartasi to'lov formasi: summa standart = qoldiq, «To'liq / 50% / 30%» chiplari, usul — tugmalar (yangi `components/TolovTanlov.jsx`) | Bir bosishda to'liq qoldiq |
| A-16 [Y] | Qaytarishda: forma tepasida «Pul zalog X — mijozga qaytariladi»; natijada «Mijozga X qaytaring · ushlab qolindi Y · qarz Z» | Natija xabarida summa |
| A-17 [Y] | Vaqtinchalik bron muddati kartada va ro'yxatda («02:06 gacha avans olinmasa bekor bo'ladi»); backend `bron_muddati` | Kartada vaqt ko'rinadi |
| A-18 [Y] | O'zgarishlar tarixi: sana-vaqt, kim, odam tilidagi matn, bo'sh holat, ochish/yopish | Xom kod/summa yo'q |
| A-20 [Y] | Telefon «Ko'proq» doim asosiy bo'limlarni ochsin, pastki paneldagilarni takrorlamasin | Kassada ham Liboslar/Mijozlar bir bosishda |
| A-31 [O] + yangi | «Qaroringiz kerak»da xarajatni joyida Tasdiqlash/Rad etish (summa, kim, izoh) | Hisobotga o'tish shart emas |
| yangi | Zakazlarda «Ertaga olib ketadi / Ertaga qaytaradi» chiplari (`BUGUN_FILTRLARI` ga 2 kalit) | Chiplar soni bilan |
| A-21 [O] | «Boshqa amallar» bo'sh bo'lsa chiqmasin; bitta band bo'lsa ichma-ich details yo'q | |
| A-26 [O] | Qadam ipi: «Bron · To'lov · Berildi · Qaytdi», joriy qadam ostida qoldiq; telefonda qisqa nomlar | |
| A-27 [O] | «Bekor qilingan» belgisi xira (`--matn-3`), qizil emas | |
| A-28 [O] | Bosh ekran jadvali Zakazlar qatori bilan bir xil (IjaraSana, muddat, qo'ng'iroq tugmasi, rasm) | |
| A-29 [O] | «Qo'ng'iroq qilish» eslatmasida qoldiq summasi | |
| A-30 [O] | To'lovlar ro'yxatida sana-vaqt, xronologik tartib, zalog bir qatorda | |
| A-32, A-33, A-35..A-38 [P] | Kassa nav → To'lov qabul (keng ekranda ham); vaqtinchalikda «Avans yo'q»; qidiruvda 300 ms kechiktirish; o'lik Click/Payme kodi olib tashlanadi; takror «Zakazlar» sarlavhasi; kartadan qaytganda skroll joyi | |

### D2 «Boshqaruv» — Liboslar, Mijozlar, Hisobot, Sozlama, backend catalog/finance
| ID | Vazifa | Qabul |
|---|---|---|
| B-01 [K] | «Tushum» so'zi faqat Foyda va zarar (kassa usuli) raqamida. Boshqa ustunlar: «Ijara narxi bo'yicha» (libos, kategoriya), «Zakazlar summasi» (sotuvchi, manba), «Kirgan pul» (pul oqimi); jadval ostida «Oylik tushum — Foyda va zarar» | 01–07.11 uchun «Tushum» nomli faqat bitta raqam |
| B-02 [Y] | Liboslar API: `mijozda`, `qaytish` (sanoq `_joylar` mantig'i); kartochkada «Mijozda · 12.11 gacha»; «Ijaraga tayyor» = bo'sh − mijozdagi; holat filtrida «Mijozda» | Berilgan 4 libos «Mijozda» |
| B-03 [Y] | P&L o'tgan oy taqqoslashi — o'tgan oyning shu kunigacha bo'lgan qismi bilan; oy nomlari «Oktabr 2026» | −63% kabi yolg'on pasayish yo'q |
| B-04 [Y] + B-14 | Hisobot turlari `optgroup` bilan 3 guruh («Pul va foyda», «Kassa va xodimlar», «Liboslar va mijozlar»); «Xarajatlar» hisobot turi olib tashlanadi (bo'lim bor); nav nomi «Hisobotlar». **«Grafik» bo'limi olib tashlanadi**, 12 oylik «Sof foyda» grafigi P&L ostiga; `OylikGrafik` standart rangi `#B9833A` | Hisobot 5 bo'lim, binafsha yo'q |
| B-05 [Y] | Rahbar libos ma'lumotini tahrirlay oladi (nomi, kategoriya, o'lcham, rang, artikul; artikul noyob; jurnalga yoziladi) | |
| B-06 [Y] | Libos holati (Sotildi/Hisobdan chiqarildi/Arxiv) — `Tasdiq` bilan; filial/yetkazib beruvchi/holat bitta «Saqlash»da | |
| B-07 [Y] | 9 ta qaytarib bo'lmaydigan amalga `Tasdiq` (ro'yxat audit B-07 da) | |
| B-08 [Y] | `Oyna`: o'zgarish bo'lsa fon/Escape da «Kiritilganlar o'chadi. Yopilsinmi?»; fokus tuzog'i; yopilgach fokus tugmaga qaytadi. **Diqqat:** `Oyna` umumiy komponent — D1/D3 oynalari ham shuni ishlatadi, API (props) o'zgarmasin | |
| B-09 [Y] | Sozlama → Avans qaytarish telefonda gorizontal skroll yo'q; qoida qatori 2 ustunli; `aria-label` | 390px da skroll 0 |
| B-10 [Y] + yangi | Xarajatlar — `.jadval-panel` jadval (Sana, Turi, Summa, Kim, Holat), kutayotganlar tepada; forma «+ Xarajat» → `Oyna`; tashqi details yo'q; jadval ostida turlar bo'yicha «bu oy / o'tgan oy» jamlanmasi | |
| B-11 [Y] | Yangi `components/OyTanlash.jsx` «‹ Noyabr 2026 ›» — barcha `type="month"` o'rniga; mahalliy sana (UTC emas) | Ruscha oy nomi yo'q |
| B-24 [Y] | Sanoqni bekor qilish (tasdiq bilan, Telegram yo'q); yakunlashdan oldin tasdiq; «Yo'q» ro'yxati jadvalda | |
| B-12 [O] | Mijoz kartasida manba select'iga «— ko'rsatilmagan —»; noma'lum qiymat ko'rsatiladi; «Telegram» varianti (backend — D1) | Saqlashda inglizcha xato yo'q |
| B-13 [O] | Kartochkadan «2:3 emas» ogohlantirishi olib tashlanadi; statlar ostida bitta qator | |
| B-15, B-16 [O] | Sodda so'zlar (audit ro'yxati); «(FT-…)» kodlari olib tashlanadi | |
| B-17 [O] | P&L ogohlantirishlarida «Ko'rsatish →» havolasi | |
| B-18 [O] | Davrga bog'liq bo'lmagan hisobot turlarida davr satri yashirin | |
| B-19 [O] | Hisobot tafsiloti kichik jadval, «#44» zakazga havola (`onZakaz`) | |
| B-20 [O] | Kunlik kassa va Xodimlar nazorati: izoh `Info` ichida; Kunlik kassada 5 asosiy ustun + «Batafsil» | |
| B-23 [O] | Placeholder-only maydonlarga yorliq | |
| B-25 [O] | Sanoq tarixidagi sana mahalliy vaqtda | |
| B-27, B-28 [O] | Rasm kattalashtirish klaviatura/Escape; sotuvchiga ruxsatsiz «×» chiqmasin (`ochira_oladi`) | |
| B-29 [O] | Majburiy maydonlar « *», o'chiq tugma ostida sababi | |
| B-32, B-33 [O/P] | Mijozlar: «200 tadan ko'p» xabari yoki «Yana»; telefon formatlangan; «keyingisi/oxirgisi»; tahrir bloki «Tahrirlash» orqali | |
| B-36 [O] (yengil) | Sozlama guruhlari mazmunga mos qayta guruhlanadi (`sozlamaBolimlari.js` — App o'zi o'qiydi); 1–3 maydonli kichik bo'limlar mumkin bo'lsa birlashtiriladi; menyu tepasida **qidiruv** | |
| B-38 [O] | Qurilmalar: sana formati, emoji o'rniga ikonka (backendsiz qismi) | |
| B-40 [P] | `--matn-3` izoh kontrasti ≥4.5:1 | |
| yangi | Katalogda o'lcham chiplari filtri | |
| B-21, B-22, B-26, B-30, B-35, B-39 [P] | Audit taklifi bo'yicha | |

### D3 «Kassa» — Kassa, Yangi zakaz, XodimMenyu, backend cash
| ID | Vazifa | Qabul |
|---|---|---|
| A-02 (frontend) [K] | To'lov qabul `holat=tolov_kutmoqda` bitta so'rov (D1 shartnomasi) | Bron 100 dan oshsa ham hammasi |
| A-03 [K] | Smena oynalaridagi xato oyna ichida (`role="alert"`), oyna ochiq qoladi | «Faqat oxirgi qolgan sotuvchi yopadi» oynada ko'rinadi |
| A-04 [K] | «Smenani yopish» faqat men ishtirokchi va yolg'iz bo'lsam; aks holda izoh + «Pulni topshirib chiqish» | 2 xodimda yopish tugmasi yo'q |
| A-05 [K] | Telefonda To'lov qabul: `.pos-zakaz` siqilmaydi (`flex: none`); tanlangach ro'yxat yig'iladi (tanlangan qator + «Boshqa zakaz»), chek `scrollIntoView`; matn yo'nalishsiz | 390px da chek va «Qabul qilish» darhol ko'rinadi |
| A-13 [Y] | Yangi mijoz: 9+ raqamda avtomatik qidiruv (300 ms); yangi mijozda F.I.O. majburiy | Ismsiz mijoz yaratilmaydi |
| A-14 [Y] | «Yangi zakaz» bo'limida smena paneli yo'q yoki telefonda bir qator; 2-qadam filtrlari telefonda «Filtr» ortida | 390px da 2-qadamda birinchi ekranda libos ko'rinadi |
| A-15 [Y] | Kategoriya tartibi backend tartibida (alifbo emas) | «Oq ko'ylak» birinchi |
| A-19 [Y] | Smenada naqd puli bor xodim «Chiqish»ni bossa ogohlantirish (+«Kassaga o'tish»); matn «Ilovadan chiqish» | |
| A-22 [O] | Smenalar tarixi: qatorda faqat ma'lumot + «Tuzatish» → `Oyna`; «Faqat farqlilar» filtri | |
| A-24 [O] | «Bandlarni ham ko'rsatish» → 2-qadam filtrlarida chip-tugma (`aria-pressed`) | |
| A-25 [O] (faqat vizual) | Smena yopishda farq katta, manfiyda qizil. «Ko'r sanash» — **ochiq savol**, qilinmaydi | |
| A-34, A-40 [P] | Rahbarda «Smenaga qo'shilish» ikkinchi darajali; smena yopiqda bitta «Smenani ochish» | |
| yangi | «Kun yakuni» kartasi Smena hisoboti tepasida: tekshirilmagan zaloglar, smenada qolgan hamkasblar, terminal sverkasi — har biri tugma bilan | |

## 3b. 2-tur (R2) vazifalari
Manba: QA hisoboti `qa/QA_R1.md` (QA-02…09, ⚠️ bandlar) va R1 backlogi. Fayl egaligi — 2-bo'limdagidek (CSS endi to'g'ridan-to'g'ri
`ichki.css` ga emas: R2 da ham har dasturchi `src/r2-d<n>.css` da yozadi, tur oxirida koordinator ko'chiradi).

**Guruhlararo shartnomalar (R2):**
- **YangiZakaz `boshlangich` prop** (D3 qabul qiladi, D1 `App.jsx` uzatadi): `{ n, dan?, gacha?, libos_id?, mijoz?: { telefon, fio } }`.
  `n` o'zgarganda qoralama tozalanib qiymatlar qo'yiladi: sana bo'lsa 1-qadam to'ldiriladi; `libos_id` bo'sh bo'lsa 2-qadamda tanlangan
  holda; `mijoz` bo'lsa 3-qadamda telefon/ism to'ldirilgan (mavjud mijoz qidiruvi ishga tushadi). Band bo'lsa — tushunarli xabar.
- **Kalendardan zakaz** (D1): bo'sh katak bosilsa `App` → `setSahifa('kassa:yangi')` + `boshlangich={ n, dan: kun, gacha: kun, libos_id }`.
- **Mijoz kartasidan zakaz** (D2 tugma → D1 App): `Mijozlar` ga prop `onYangiZakaz({ telefon, fio })` → `boshlangich={ n, mijoz }`.
- **To'lovdan keyin «Libosni berish →»** (D3 tugma → D1 App/Zakazlar): `Kassa` ga prop `onZakaz(id, amal)`; `amal === 'berish'` bo'lsa
  zakaz kartasi ochilib asosiy amal (berish formasi) ko'rinadigan joyga suriladi. Tugma: to'lovdan keyin zakaz `bron`, qoldiq 0, olib ketish ≤ bugun.
- **A-39** (D1 backend, D3 frontend): `GET /api/mijozlar/qidirish/?telefon=` topilmasa **200** `{ "topildi": false }` (404 emas);
  topilsa avvalgi obyekt + `"topildi": true`. Barcha iste'molchilar moslanadi (grep `mijozQidir`).
- **Sozlamalar `onBolim`** (D1): `onBolim={(b) => setSahifa('sozlamalar:' + b)}` — sozlama qidiruvidan tanlanganda chap menyu guruhi ham ochiladi.

| Guruh | Vazifalar |
|---|---|
| **D1** | QA-02 [Y] telefonda qadam ipi izohi ustma-ust tushmasin (izoh qadam ipidan tashqarida yoki faqat joriy qadam nomi); QA-05 bron muddati kartada bir marta; QA-06 «+ Yangi zakaz» qidiruv bilan bir qatorda o'ngda; QA-07 nav nomi «Oylik foyda» (D2 sahifa sarlavhasi bilan bir xil); yuqoridagi shartnomalarning App/Kalendar/Zakazlar/backend qismi; **sotuvchi bildirishnomalari** — sotuvchiga ham qo'ng'iroqcha: chegirma so'rovi natijasi (tasdiq/rad), unga topshirilgan va hali qabul qilinmagan pul, bugungi qo'ng'iroqlar soni (yangi `GET /api/bildirishnomalar/`, orders ichida, cash'dan faqat o'qiydi); yangi oqimlar uchun E2E testlar |
| **D2** | QA-03 «(sverka)» → oddiy so'z (Sozlama · Kassa); QA-07 sahifa sarlavhasi «Oylik foyda»; QA-08 telefonda «Turlar bo'yicha» oxirgi ustuni kesilmasin; QA-09 jurnalda summa `som()` va holat nomi; B-37 har sozlama bo'limida bitta saqlash usuli; B-31 aksessuar tafsiloti tartibi; B-34 Salonchilar `.jadval-panel` jadvali va «+ Salonchi» oynasi; **libos pasporti** (tafsilotda: hozir kimda/qachon qaytadi, kelgusi bronlar ro'yxati, rahbarga — necha marta berilgan, tushum, qoplash); ikki zalog hisobotini bittaga birlashtirish; Mijoz kartasida «Yangi zakaz» tugmasi (`onYangiZakaz`); yangi oqimlar uchun E2E |
| **D3** | QA-03 Kassada «Xarajat moddasi» → «Xarajat turi», «Terminal sverkasi» → «Terminal hisoboti»; QA-04 Smena hisobotida «Tushum» → «Kirgan pul (avans + qoldiq + jarima)»; telefonda To'lov qabulda «Ro'yxatdan zakazni tanlang» bo'sh kartasi zakaz tanlanmaguncha yashirin; YangiZakaz `boshlangich` prop; Kassa to'lov muvaffaqiyatida «Libosni berish →» (`onZakaz`); A-39 frontend qismi; yangi oqimlar uchun E2E |

## 3c. 3-tur (R3) vazifalari — chuqur oqimlar (C-audit) va QA R2
Manba: `audit/C_R2.md` (31 topilma, dalillari bilan), `qa/QA_R2.md`. **R3 da fayl egaligi o'zgaradi** (bitta faylda ikki dasturchi bo'lmasin):
| Guruh | Frontend | Backend |
|---|---|---|
| **D1** | `Zakazlar.jsx`, `BoshEkran.jsx`, `Dashbord.jsx`, `Kalendar.jsx`, `App.jsx`, `Oflayn.jsx`, `components/{Hujjat,Tasdiq,UstkiPanel,TolovTanlov}.jsx`, `api/index.js` (yangi funksiyalar) | `orders/views_royxat.py`, `orders/tarix_matni.py`, bildirishnomalar |
| **D2** | R2 dagi fayllar | `catalog`, `finance`, `tenants/permissions.py` (begona `models.py`/`views.py` ga tegilmaydi) |
| **D3** | `Kassa.jsx`, `YangiZakaz.jsx`, `XodimMenyu.jsx` | `cash`, `bookings`, `orders/{rental,changes,hujjatlar,discounts,services,promo,views}.py` va ularning testlari; `tenants/models.py` da **faqat** `avans_foizi` maydoni + `tenants/0038` (begona `rahbar_faol` qatorlariga tegilmaydi) |
CSS: `src/r3-d<n>.css`.

**API shartnomalari (D3 backend → D1 UI):**
- C-03: «kelmadi» deb belgilangan o'tkazma qoldiq qarz bo'lib qoladi; **zakaz `tolangan < jami` bo'lsa `yopildi` ga o'tmaydi** (qaytarilgan bo'lsa `qaytarildi` da turadi). `berildi`/`qaytarildi` zakazga `qoldiq` to'lovi qabul qilinadi (backend allaqachon ruxsat bersa — tekshir). D1: kartada shu holatlarda ham qoldiq formasi; `tolov_kutmoqda` filtri bu zakazlarni ham qaytaradi. D3: Kassada «Kelmadi» — `Tasdiq` oynasi bilan («#123 dan 1 500 000 qarz bo'ladi»).
- C-05: tarixga yangi harakatlar yoziladi: `chegirma_soraldi`, `chegirma_qarori`, `promokod`, `berildi`, `qaytarildi`, `qarz_tolandi`, `otkazma_kelmadi`, `salonchi` (eski/yangi qiymat va sabab bilan). D1 `tarix_matni.py` da ularning odam tilidagi nomi.
- C-07: to'liq to'langan zakazda narx kamaysa — o'zgarish qilinadi va farq mijozga qaytariladi (`VOZVRAT`, usul tanlanadi); xato matni bekor qilishni tavsiya qilmaydi. Javobda `yangi_jami`, `qaytariladi`. C-17: sana ko'chirish/almashtirish javobida `yangi_jami`, `qoldiq`.
- C-08: erta berishda bron boshlanishi bugunga ko'chadi (to'qnashuv bo'lsa — rad, aniq xabar); bandlik tekshiruvi `berildi` zakazlarni ham hisobga oladi.
- C-10: qaytarishda «yirtiq»/«dog'» — libos `tamirda` (ta'mir jurnaliga yozuv), «tozalashda» emas; «aksessuar yo'q» — `yoqolgan_donalar: [dona_id]` qabul qilinadi, dona `yoqolgan`.
- C-20: bekor qilishdagi qaytarim, qaytarishdagi jarima va qarz to'lovi `usul` qabul qiladi (naqd/terminal/o'tkazma); rahbar bekor qilishda `qaytariladigan_foiz` ni o'zgartira oladi (backend bor — UI D1).
- C-09/C-29: kvitansiya — qaytarilgan pul manfiy va «Qaytarildi» deb, «kelmadi» o'tkazma ustidan chizilgan, bekor qilingan zakazda «Qoldiq» yo'q; dalolatnoma — jarima zalogdan ushlangani; shartnoma «Zalog» bandida summa.
- C-26: tillo og'irligi mos kelmasa xato matni kutilgan og'irlikni aytmaydi.

| Guruh | Vazifalar |
|---|---|
| **D1** | C-01 [K] zakaz kartasida varaq yopishqoq emas (sticky faqat Yangi zakazda) — 1024×768 da hujjat tugmalari bosiladi; C-02 [K] chop etishda faqat hujjat (shapka, menyu, chekinish yo'q); C-04 [K] bekor qilish tasdig'ida va natijada «Mijozga X qaytariladi · Y ushlab qolinadi» (+ usul, rahbarga foizni o'zgartirish); C-03/C-05/C-07/C-17/C-19/C-26 UI qismlari; C-06 chegirma kutilganda kartada nima so'ralgani, so'rovni qaytarib olish, bron muddati; C-15 tayyor chegirma tugmasida summa + tasdiq + olib tashlash; C-16 rahbar qarorida yangi jami, summani o'zgartirish, rad sababi; C-18 berish formasi: avval tekshiruv, keyin erta berish tasdig'i, `select` yorlig'i, FT-kod ko'rinmasin; C-14 tarmoq xatosi forma holatini yo'qotmasin (oflaynga faqat `navigator.onLine===false` yoki ketma-ket 2+ xato); C-22 oflayn kontrast va qoldiq; C-23 «Davom etyapsizmi?» tugmalari: «Chiqish» / «Ha, davom etaman» + sanoq; C-24 sotuvchiga «o'tkazma kelmadi» va «xarajatingiz rad etildi» ilovada; C-28 hujjat «← Orqaga» kontrasti; C-30 1024 px da «Dashboard» sinmasin; C-31 olib tashlashdan keyin yangi jami; QA R2 dagi D1 bandlari |
| **D2** | C-11 (hisobot qismi) seyf farqi Kunlik kassa va Xodimlar nazoratida; C-12 (matn qismi) `SalonYozishRuxsati` xabari o'zbekcha, aniq sabab bilan; C-25 sotuvchi qo'shgan libos unga «Tasdiq kutilmoqda» bo'lib ko'rinsin, rahbarda «Rad etish»; QA R2 dagi D2 bandlari |
| **D3** | yuqoridagi barcha backend shartnomalar (testlari bilan); C-11 seyf farqi `Smena` da saqlanadi (migratsiya) va ochish oynasida jonli farq + farq bo'lsa izoh; C-13 Yangi zakaz qoralamasi xodimga bog'lanadi (boshqa xodimga ochilmaydi); C-27 inkassatsiya tugmasi matni; QA R2 dagi D3 bandlari |
**Foydalanuvchi qarorlari (2026-11-07) bo'yicha R3 ga qo'shiladi:**
- **C-12 → (b)**: «faqat ko'rish» salonida **yangi zakaz, katalog, sozlamalar, xarajat** to'xtaydi; **mavjud zakazni yakunlash** ishlaydi — to'lov
  (avans/qoldiq/qarz), berish, qaytarish, zalogni qaytarish, smena ochish/qo'shilish/chiqish/yopish, pul topshirish/qabul. D2: `tenants/permissions.py`
  da mexanizm — view'da `faqat_korishda_ruxsat = True` bo'lsa yozishga ruxsat, aks holda o'zbekcha xabar («Obuna muddati tugagan: yangi zakaz,
  katalog va sozlamalar yopiq. Boshlangan zakazlarni yakunlash mumkin.»). D3: `cash/views.py` va `orders/views.py` dagi tegishli view'larga shu belgi
  (R3 da `orders/views.py` — D3 niki). D1: banner matni shu ma'noda; to'xtaydigan tugmalar (Yangi zakaz, «+») o'chiq ko'rinsin.
- **C-21 → har salon o'zi sozlaydi**: yangi sozlama `SalonSozlamalari.avans_foizi` (PositiveSmallInteger, null, 1–100). `null` — hozirgi xatti-harakat
  (avans sifatida olingan to'lov to'liq avans); son — **avans zakaz jamining shu foizigacha**, ortig'i «oldindan to'lov» bo'lib bekor qilishda to'liq
  qaytariladi (`qaytarish_asosi='avans'` bo'lganda; `'tolangan'` da avvalgidek hammasi). D3: maydon + migratsiya `tenants/0038` (begona `0037` dan keyin —
  **commit qilishda 0037 bilan birga** bo'lishi kerak), `changes.zakazni_bekor_qilish` hisobi, shartnomaning avtomatik bandi tanlangan qoidani aniq
  yozsin (misol bilan), testlar. D2: Sozlama → «Avans qaytarish» bo'limida tanlov: «Birinchi to'lov to'liq avans» / «Avans — zakazning __% i, ortig'i
  to'liq qaytariladi» (oddiy tilda, misol qatori bilan: «3 000 000 lik zakazda 30% → avans 900 000»).
- **A-25 → (a)**: «ko'r sanash» qilinmaydi — tizim summasi ko'rinib turadi. C-11 dan faqat ko'r sanashga tegishli bo'lmagan qism qoladi
  (seyf farqi saqlanadi, ochishda jonli farq va farq bo'lsa izoh, hisobotlarda ko'rinadi).

## 4. Keyingi turlarga qoldirilganlar (backlog)
> 2026-11-07 tekshirildi. R1 backlogining ko'pi R2 da bajarildi: A-23 (kalendardan zakaz), «Libosni berish →», sotuvchi qo'ng'iroqchasi,
> libos pasporti (B yangi-1), mijoz kartasidan «Yangi zakaz» (B yangi-3), B-37, B-31, B-34, A-39, zaloglar bitta hisobot (B-04 qismi).
> R1/R3 dagi «qisman» bandlar ham keyin yopildi: A-19 (`onKassa` ulangan), C-06 (so'rovni qaytarib olish), C-15 (chegirmani olib tashlash) —
> `DELETE /zakazlar/<id>/chegirma/` R3 da qo'shilgan, `Zakazlar.jsx` dagi `CHEGIRMA_OLIB_TASHLASH = true`.

**Qolganlari:**
- **B-38 (qisman)** — Sozlama → qurilmalar: «Shu qurilma» belgisi va «Eskilarini chiqarish». Backend `tenants` da — u fayllarda foydalanuvchining
  commit qilinmagan `rahbar_faol` o'zgarishi bor, shuning uchun tegilmadi. U commit qilingach qilinadi.
- ~~**Yangi kuzatuv (2026-11-08)** — erta qaytgan/yopilgan zakaz broni libosni arxivga/sotilganga o'tkazishni va donani ta'mirga berishni
  bron oxirigacha to'sardi.~~ ✅ **2026-11-08 tuzatildi:** `Bron.kelgusi()` va `AksessuarBron.kelgusi()` `zakaz__holat` qaytarildi/yopildi/bekor
  bronlarni chiqarib tashlaydi (`bookings/models.py`, `YAKUNLANGAN_ZAKAZ`); bandlik (bufer) bronlari saqlanadi. Testlar
  `orders.test_r3.YakunlanganZakazBroniTests` (3; tuzatishsiz 2 tasi yiqiladi), E2E `kassa-davomi` vaqtinchalik libosni arxivga o'tkazadi.
- **B yangi-4** — sanoqni qisman o'tkazish (faqat aksessuarlar yoki bitta kategoriya) va bekor qilinganda Telegramga yubormaslik (`B_R1.md:77`). Hajm M, backend kerak.
- **Boshqa bo'limlarni «DressRent Pro» uslubiga moslash** — reja `docs/UX_USLUB.md` 4-bo'limida (Zakazlar, Liboslar, Mijozlar, Kassa, Hisobotlar,
  Sozlama). Foydalanuvchi ruxsatini kutadi. ChatGPT/Browns andozasidagi dizayn kanvasi (`dizayn/DIZAYN_R1.md`) loyihaga o'tkazilmadi — uning
  o'rnini shu yo'nalish egalladi.

## 5. Ochiq savollar (foydalanuvchi qarori kerak)
> **2026-11-07 javoblar:** 1 → (a) hozirgidek; 2 → (b); 3 → «har salonda har xil qoida sozlanadigan bo'lishi kerak» (3c-bo'limga qarang).
4. **QA-17 Qoidani zakazga qotirish**: bekor qilish qoidasi va `avans_foizi` zakaz yaratilgan paytda saqlanmaydi — salon sozlamani keyin
   o'zgartirsa, eski zakazlarning shartnoma matni va bekor qilish summasi ham o'zgaradi. Misol: kelin 30% qoidasi bilan shartnoma imzoladi,
   salon keyin 50% qildi — bekor qilsa unga yangi (yomonroq) qoida qo'llanadi. Variantlar: (a) hozirgidek (doim joriy sozlama);
   (b) zakaz yaratilganda qoida zakazga yoziladi, eski zakazlar o'z qoidasida qoladi. Tavsiya: (b) — imzolangan shartnomaga mos.
   > **2026-11-07 javob: (b).** R5 da D3: `Zakaz.qaytarish_qoidasi/qaytarish_asosi/avans_foizi` (migratsiya `orders/0017`), yaratishda nusxa,
   > bekor qilish/oldindan hisob/shartnoma avval zakazdagi qiymatni, bo'sh bo'lsa salon sozlamasini ishlatadi.
1. **A-25 «Ko'r sanash»**: smena yopishda xodim pulni sanaguncha tizimdagi summa ko'rsatilmasinmi? Hozir u ko'rinib turadi va farq yozish
   bilan jonli o'zgaradi — xodim «farq yo'q» chiqquncha raqamni moslab qo'yishi mumkin. Variantlar: (a) hozirgidek; (b) tizim summasi faqat
   «Yopish» tasdiq oynasida ko'rinadi. Koordinator tavsiyasi: (b) — egasining «kamomad bormi» savoliga halol javob. (C-11: smena ochishdagi seyf sanog'iga ham tegishli.)
2. **C-12 «Faqat ko'rish» (obuna tugagan) rejimi**: hozir backend hamma yozuvni to'xtatadi — to'lov, libos berish, qaytarish, zalogni qaytarish,
   smenani yopish ham. Masalan, to'yi ertaga bo'lgan, pulini to'liq to'lagan kelinga libos berilmaydi; qaytgan mijozning zalogi qaytarilmaydi.
   Variantlar: (a) hozirgidek hammasi to'xtaydi; (b) yangi zakaz, katalog va sozlamalar to'xtaydi, **mavjud zakazlarni yakunlash** (to'lov, berish,
   qaytarish, zalog, smena yopish) ishlaydi. Tavsiya: (b) — mijoz zarar ko'rmaydi, salon baribir obunani to'lashga majbur (yangi zakaz yo'q).
3. **C-21 Oldindan to'liq to'langan pulning bekor qilishdagi taqdiri**: birinchi to'lov summasidan qat'i nazar «avans» deb yoziladi. Misol: zakaz
   3 000 000; A mijoz 900 000 avans berdi, B mijoz 3 000 000 ni birdan to'ladi; 7–29 kun qolganda bekor qilsa (50% qoida) A 450 000, B esa
   1 500 000 yo'qotadi. Shartnomada esa «avansdan tashqari oldindan to'langan summa to'liq qaytariladi» deyilgan — tizim shartnomaga zid.
   Variantlar: (a) shartnoma matnini tizimga moslash (hamma to'langan avans); (b) avans = zakazning sozlamadagi foizi (masalan 30%), ortig'i
   «oldindan to'lov» — to'liq qaytariladi. Tavsiya: (b) — shartnomaga mos va mijozga adolatli.

## 6. Qabul qilingan qarorlar (sababi bilan)
- Rasmiy «Tushum» = P&L kassa usuli — egasi uchun bitta raqam; boshqalari ma'nosiga ko'ra nomlanadi (B-01).
- «Grafik» bo'limi olib tashlanadi — Dashboard grafigini takrorlaydi; sof foyda grafigi P&L ga ko'chadi (B-14).
- Ro'yxat API ga sahifalash orqaga mos qo'shiladi (`sahifa=1` bo'lsa obyekt) — E2E va boshqa iste'molchilar buzilmasin.
- Parallel ish uchun CSS dasturchi fayllarida (`r1-d*.css`), tur oxirida `ichki.css` ga ko'chiriladi.

## 7. Holat
| Tur | Sana | Holat | Hujjatlar |
|---|---|---|---|
| R1 audit | 2026-11-07 | ✅ tugadi (A: 40, B: 40 topilma) | `audit/A_R1.md`, `audit/B_R1.md` |
| R1 dasturlash | 2026-11-07 | ✅ tugadi. D1: barcha bandlar (A-23 backlog), orders 305 + bookings 17 test; D2: K/Y hammasi, B-38 va B-40 qisman, catalog+finance 267 test; D3: 13/14 (A-19 qisman → D1 `onKassa` uzatdi), cash 74 test. E2E spec'lar yangilandi, to'liq E2E 23/23 (D2 yugurishi). `r1-d*.css` → `ichki.css` oxiriga ko'chirildi, `--matn-3` → `index.css` | `dev/DEV1_R1.md`, `DEV2_R1.md`, `DEV3_R1.md` |
| R1 QA | 2026-11-07 | ✅ lint 0 xato, build OK, backend 857 (855 OK: notify 2 — biri R1 matni, koordinator testni moslab tuzatdi; ikkinchisi begona `rahbar_faol` o'zgarishi), E2E 23/23, tur xatosi 0, K/Y 33/33 ✅ | `qa/QA_R1.md` |
| R2 dasturlash | 2026-11-07 | ✅ tugadi. D1: shartnomalar, QA-02/05/06/07, sotuvchi qo'ng'iroqchasi (`GET /api/bildirishnomalar/`), orders 309; D2: QA-03/07/08/09, B-37, B-31, B-34, libos pasporti (`GET /api/liboslar/<id>/pasport/`), «Zaloglar» bitta hisobot (`zalog-statistika` olib tashlandi), catalog+finance 268; D3: QA-03/04, `boshlangich`, «Libosni berish →», A-39, cash 74. Yangi E2E: `kassa-davomi`, `zz-boshqaruv`, `bildirishnoma`. `r2-d*.css` → `ichki.css` | `dev/DEV*_R2.md` |
| R2 QA | 2026-11-07 | ✅ lint/build OK, backend 862 (861 — notify `:391` begona), E2E 31 (30; `zz-bank` — QA-11 → D1 R3), tur xatosi 0, R2 29/30 ✅, guruhlararo 6 oqim jonli ishladi | `qa/QA_R2.md` |
| R2 audit C | 2026-11-07 | ✅ 31 topilma (K 4, Y 10) → R3 | `audit/C_R2.md` |
| R3 dasturlash | 2026-11-07 | ✅ tugadi. D3: pul mantig'i backendi (C-03, 05, 07, 08, 09, 10, 11, 13, 20, 21, 26, 27, 29), `DELETE …/chegirma/`, `GET …/bekor/` (oldindan hisob), migratsiyalar `tenants/0038` (`avans_foizi`; begona `0037` bilan birga commit), `cash/0007` (seyf farqi); cash+bookings+orders 432 OK. D1: C-01, 02, 04, 03/07/17/19/20 UI, 06, 14, 15, 16, 18, 22, 23, 24, 28, 30, 31, QA-11, QA-12; yangi E2E `zzz-zakaz-pul`. D2: C-12 mexanizmi (`faqat_korishda_ruxsat`, `yozish_taqiqi`, 7 fayl o'tkazildi; texnik yordam va primerka ochiq), C-21 sozlama UI, C-11 hisobotlarda, C-25 (`POST /liboslar/<id>/rad/`) | `dev/DEV*_R3.md` |
| R3 QA | 2026-11-07 | ⏳ qisman: lint/build OK, backend 905 (904 — notify `:391` begona), makemigrations toza, egasiz fayllardagi D2/D3 tahrirlari joyida; E2E 37 (34 ✅; `zzz-zakaz-pul` 1-testi `zakaz-oqimi` qoldirgan «tozalashda» libosga bog'liq → D1 tuzatmoqda). **Qoldi:** :8002 ga bog'liq jonli tekshiruvlar (tur r3/s3, pul oqimlari C-03/04/07/08/10/20/21, C-12, C-01/02/11/13/14) — ko'rik backendi xotira tanqisligida tizim tomonidan o'chirildi, foydalanuvchi ruxsati bilan qayta yoqiladi (TZ 1-bo'lim buyrug'i) | `qa/QA_R3.md` |
| R3 QA (yakuniy) | 2026-11-07 | ✅ E2E 37/37, backend 905 (904 — begona notify `:391`), tur xatosi 0, R3 28/30 ✅; pul oqimlari C-03/04/07/08/10/20/21 jonli ishladi (C-21: 3 000 000 to'liq to'langan, 30% → 2 550 000 qaytdi, 450 000 ushlandi). ❌ QA-15 (faqat ko'rishda katalog ochiq) → R4 | `qa/QA_R3.md` |
| R4 (kichik tuzatishlar) | 2026-11-07 | ✅ D2: QA-15 (faqat ko'rishda katalog yopiq, 14 yozuv turi testda), QA-18 (`IsStaff`/`IsRahbar` o'zbekcha); D3: QA-16; D1: QA-14. Har biri o'z testlari bilan; **to'liq to'plam R4+R5 dan keyin qayta yugurilmagan** | `dev/DEV*_R4.md` |
| R5 (QA-17 → b) | 2026-11-07 | ✅ D3: `Zakaz` ga qoida nusxasi (migratsiya `orders/0017`), bekor/oldindan hisob/shartnoma shundan; orders+cash+bookings 436 OK | `dev/DEV3_R5.md` |
| Yangi Dashboard — 1-variant (foydalanuvchi maketi «DressRent Pro» asosida, agentsiz) | 2026-11-07 | ✅ (keyingi qatorda o'zgartirilgan) eski uslub saqlangan: davr (7/30/90 kun) va 4 ko'rsatkich (oldingi teng davr bilan halol foiz), egasining 3 savoli, bugungi ishlar, tushum dinamikasi (SVG chiziq, oldingi davr uzuq, sichqoncha/klaviatura izohi), eng ko'p ijaraga berilgan 3 libos (rasmli), yaqin bronlar, liboslar holati halqasi, filiallar (bo'lsa), tezkor amallar («Libos qo'shish» oynani ochadi). Backend `GET /api/dashbord/panel/?kun=&filial=` (`orders/views_panel.py`, test 6). Olib tashlandi: kun varaqasi, bandlik o'lchagichi, 12 oylik grafik (Oylik foydada bor), `Olchagich.jsx`. E2E `bolimlar` yangilandi; bolimlar+kassa-topshirish+korinish 10/10, build OK. Reklama banneri va promo karta ataylab olinmadi | `ichki-yaxshilash\natija\13–15` |
| Dashboard — 2-variant (foydalanuvchi izohlari bo'yicha) | 2026-11-07 | ✅ **Joriy holat.** Tartib maketdagidek: 1) 4 ko'rsatkich; 2) Tushum dinamikasi · Eng ko'p ijaraga berilgan · Yaqin bronlar (o'ngda); 3) Bugun kassada (filial bo'lsa — Filiallar) · Liboslar holati · Nazorat (egasining savollari) · Tezkor amallar (o'ngda). Nisbatlar maketdan (2-qator 512:479:277, 3-qator 345:302:351:263), keng ekranda `main` 1720 px gacha. Davr tanlovi — «Tushum dinamikasi» kartasida ixcham «30 kun ⌄». **Dashboard'da yo'q** (foydalanuvchi qarori): «Qaroringiz kerak», «Salonni sozlash», kundalik ish kartalari. **Qo'ng'iroqcha menyusi** (`UstkiPanel`): «Salonni sozlash n/jami» (progress, qolgan qadamlar, «Yashirish») → «Qaroringiz kerak» (`Tasdiqlar`, Tasdiqlash/Rad etish joyida, menyu ochilganda yangilanadi) → bildirishnomalar → Telegram ulash. **Kundalik kartalar** (Bugun olib ketadi, Bugun qaytaradi, Kechikkan, Qo'ng'iroq qilish, Qoldiq to'lanmagan) — faqat xodim bosh sahifasida (`BoshEkran`, `.ishlar-tor`, faqat ish bor tur chiqadi); rahbarda faqat «Qarzdorlar» (bo'lsa). Bildirishnomalar rolga qarab (`views_bildirishnoma`): olib/qaytar/qo'ng'iroq — xodimga, kechikkan — hammaga, qarzdor — rahbarga. Sotuvchi xarajati rahbarga Telegram botda (`finance.services.xarajat_kiritish` → `rahbarlarga(..., 'xarajat_tasdiq')`; chegirma avvaldan). Testlar: `finance.tests`, `orders.test_r2`, `orders.test_panel` 42/42; E2E 18/18 (bildirishnoma, bolimlar, kassa-topshirish, korinish, mobil, zz-amallar, zz-bank). Brauzerda (Chrome, foydalanuvchi ekrani kengligida) maket bilan solishtirildi. Uslub qo'llanmasi: `docs/UX_USLUB.md` | `PROGRESS.md` (51) |
| Dizayn (ChatGPT/Browns andozasi asosida UX maketi) | 2026-11-07 | ⏸ kanvas `https://claude.ai/artifact/Gqe4HTznX6f99bKqDSiA5p` loyihaga o'tkazilmadi — o'rniga foydalanuvchining «DressRent Pro» maketi bo'yicha Dashboard qilindi (yuqoridagi 2 qator) | `dizayn/DIZAYN_R1.md` |
| To'liq tekshiruv (R4 + R5 + Dashboard'dan keyin) | 2026-11-08 | ✅ **backend 918: 916 OK**, 2 yiqildi — ikkalasi bizning o'zgarishdan emas: (1) begona `rahbar_faol` → `notify/tests.py:391` (ma'lum); (2) `tenants.test_infra.test_testlarda_bugun_sobit` — yugurish yarim tundan o'tdi, `config/test_runner.py` siljishni boshida bir marta hisoblaydi (qayta yugurganda 5/5 OK). **E2E 38/38** (5,7 daq). 1-yugurishda `korinish` «libos sanog'i» yiqildi: R4 dagi `kassa-davomi` QA-16 testi o'z `QA16` libosini salonda qoldiradi → sanoqda «Yo'q (2)». Tuzatildi: sanoq testi aniq son o'rniga E2E-2 bor, skaner qilinganlar yo'qligini tekshiradi. **Build OK**, **lint 0 xato / 14 ogohlantirish** (o'zgarmagan) | |
| Bron tuzatishi (backlogdan) | 2026-11-08 | ✅ yakunlangan zakaz broni arxiv/ta'mirni to'smaydi (4-bo'lim). bookings+catalog+orders 519/519, E2E 38/38 | |
| Bo'limlarni maket uslubiga moslash — 1. Zakazlar | 2026-11-08 | ✅ ko'rsatkich kartalari-filtr, o'ngda «Bugun» ustuni (≥1440), telefonda ixcham — tafsilot `docs/UX_USLUB.md` 4-bo'lim. orders ro'yxat testlari 52/52, E2E 38/38, build OK, lint 0 xato / 14. Skrinshotlar E2E muhitidan (`frontend/test-results/zakazlar/`); ko'rik serveri (:8002) foydalanuvchi ruxsatini kutmoqda | |
| 2. Liboslar, 3. Mijozlar | 2026-11-08 | ✅ umumiy `components/KpiFiltr.jsx` (Zakazlar ham shunga o'tdi), telefonda ixcham `.kpi-filtrlar`. Liboslar: kartalar-filtr + chapda filtr ustuni (≥1280). Mijozlar: rahbar kartalari + backend `mijozlar/sonlar/`, `?tur=` (test `orders.test_mijoz.MijozSonlariTests`). Sotuvchi bosh sahifasidagi «Yuklanmoqda» kartasi E2E'ni ba'zan yiqitardi — klassi ajratildi. E2E 38/38 | |
| 4. Kassa, 5. Hisobotlar | 2026-11-08 | ✅ Kassa → Smena hisoboti: 4 ko'rsatkich (so'mgacha aniq) + «Kun yakuni»/«Naqd pul hisobi» yonma-yon. Hisobotlar: Oylik foyda 4 karta (o'tgan oy bilan), Umumiy hisobot — jami qatoridan ko'rsatkichlar + oldingi teng davr. Backend o'zgarmadi. E2E 38/38, build OK, lint 0 xato/14. | |
| 6. Sozlama | 2026-11-08 | ✅ «Barcha sozlamalar» kirish ekrani (guruh kartalari, har bo'limda izoh) + chap menyuda unga qaytish tugmasi. **Rejadagi 6 bo'limning hammasi maket uslubiga o'tdi** (Zakazlar, Liboslar, Mijozlar, Kassa, Hisobotlar, Sozlama). E2E 38/38, build OK, lint 0 xato/14. **To'liq backend 923: 922 OK**, 1 yiqildi — begona `rahbar_faol` → `notify/tests.py:391` (ma'lum). Yangi testlar: `YakunlanganZakazBroniTests` (3), `MijozSonlariTests` (2), `tolov_kutmoqda` soni | |
| **Keyingi qadam** | — | 1) Boshqa bo'limlarni `docs/UX_USLUB.md` bo'yicha moslash — **foydalanuvchi ruxsati bilan**, bo'limma-bo'lim, har biridan keyin natijani ko'rsatib to'xtash (sub-agent jamoasisiz — foydalanuvchi qarori, xarajat sababli); 2) backlog (4-bo'lim); 3) deploydan oldin `npm audit` va `pip-audit`; 4) commit — faqat foydalanuvchi so'raganda (`tenants/0037` + `0038` birga) | |

**R1 da qo'shilgan API (orqaga mos):** `zakazlar/royxat/?holat=tolov_kutmoqda|faol|ertaga_olib|ertaga_qaytar`, `?sahifa=1&limit&offset` → `{natija, jami}`;
qatorlarda `qoldiq`, `bron_muddati`; `mijozlar/?sahifa=1` → `{natija, jami}`; `Mijoz.manba` + `telegram` (migratsiya `orders/0016`);
qaytarish javobida `mijozga_qaytariladi`; tarixda `nomi`, `matn`; liboslarda `mijozda`, `qaytish`, rasmda `ochira_oladi`;
`PATCH /liboslar/<id>/` — artikul, nom, kategoriya, o'lcham, rang; `DELETE /api/sanoq/` — ochiq sanoqni bekor qilish;
hisobotlarda `davrsiz`, `zakazlar`; P&L taqqoslashda `gacha_kun`, `qisman`; `kassa/smenalar/?farqli=1`.
**Ish tartibi bo'yicha saboq:** 7,7 GB RAM da 3 dasturchi + serverlar + Playwright parallel ishlaganda xotira tugaydi — har agent bir vaqtda bitta og'ir
jarayon ishlatsin; Python satrida `'` bo'lsa qo'sh tirnoq (yarim qolgan tahrir umumiy serverni yiqitgan edi).
