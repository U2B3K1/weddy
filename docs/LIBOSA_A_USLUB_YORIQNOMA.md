# Libosa ichki sahifalari: «A. Qasr kechasi» uslubi bo'yicha yo'riqnoma

Bu fayl ichki ilova sahifalarini (xodim kirgandan keyingi hamma ekranlar) «A. Qasr kechasi» uslubiga o'tkazadigan agent uchun yozilgan.

- **Namuna maket:** https://claude.ai/artifact/Ba4CmSaGtur9rKE4Rr24e1. Unda «A. Qasr kechasi» artboardi bor, ochilmasa shu fayl yetarli.
- **UX muammolari ro'yxati:** `Libosa_UI_UX_takliflar_v1.md` (agar papkada bo'lsa).
- **Loyiha:** `F:\Project_Antigravity\weddy`. Frontend: `frontend/src` (React + Vite).

---

## 0. Ishni boshlashdan oldin

1. `PROGRESS.md` ni o'qing. Unda oxirgi o'zgarishlar va qoidalar yozilgan.
2. Quyidagi fayllarni o'qing: `frontend/src/index.css`, `App.jsx`, `components/Shapka.jsx`, `pages/PlatformaFon.jsx`, `pages/platforma-fon.css`.
3. **Mantiqqa tegmang.** API chaqiruvlari, state, ruxsatlar (rahbar/sotuvchi) va TZ qoidalari o'zgarmaydi. O'zgaradi: CSS, JSX tuzilishi (o'rash, tartib, sinflar) va matnlar.
4. Bosh sahifaga (`Reklama.jsx`, `reklama.css`, `reklamaSahna.js`) **tegmang**. Uslub o'sha yerdan olinadi, lekin u o'zgarmaydi.
5. Har bosqichdan keyin `npm run build` ishga tushiring va natijani `PROGRESS.md` ga bir qisqa yozuv sifatida qo'shing.

---

## 1. Uslub g'oyasi (bir jumlada)

Bosh sahifadagi kayfiyat ichkarida ham davom etadi: **to'q tun foni, tepadan tushadigan yumshoq tilla nur, shishasimon panellar, tilla pill tugmalar, Forum sarlavhalar va Cormorant kursiv urg'ular.** Ish ekranlari baribir o'qilishi oson bo'lishi shart: panellar zich, matn yorqin.

---

## 2. Ranglar va tokenlar

`index.css` dagi `:root` ni shu tokenlar bilan almashtiring. Eski nomlar (`--tilla`, `--tilla-toq`, `--siyoh`, `--oq`, `--matn`) qolsin, chunki kod ularni ishlatadi. Ishlatilmayotgan `--rang: #8b5e83` olib tashlansin.

```css
:root {
  /* fon */
  --tun: #0B1220;            /* asosiy fon */
  --tun-chuqur: #070C16;     /* eng past qatlam */
  /* panellar (shisha) */
  --shisha: rgba(22, 35, 58, .78);       /* kartalar; .78 dan shaffof QILMANG */
  --shisha-ichki: rgba(251, 246, 238, .06);
  --shisha-chet: rgba(228, 193, 150, .28);
  --shisha-chet-faol: #E4C196;
  /* brend */
  --tilla: #E4C196;          /* och tilla: urg'u matni, faol chegara */
  --tilla-toq: #CC9866;      /* EZAZ tilla */
  --kok: #2F496E;            /* EZAZ ko'k: tanlangan, grafik */
  --siyoh: #141B26;          /* tilla tugma ustidagi matn */
  /* matn */
  --oq: #FBF6EE;             /* asosiy matn */
  --matn: #FBF6EE;
  --matn-2: #C7CFDA;         /* ikkinchi darajali; panelda ~10:1 */
  /* holat */
  --yaxshi: #7ED6A0;
  --xavf: #FF9B92;
  --ogoh: #F2C46D;
  --ber: #8DB4E8;            /* «Berildi» holati */
  /* shakl */
  --r-panel: 20px; --r-ichki: 14px; --r-tugma: 999px;
  --serif: 'Casagrande Deco', 'Forum', Georgia, serif;
  --kursiv: 'Cormorant Garamond', Georgia, serif;
  --sans: 'Manrope', system-ui, sans-serif;
}
```

**Kontrast qoidalari (o'lchangan):**

| Juftlik | Nisbat |
|---|---|
| Tilla #CC9866 → #0B1220 fonida | 7.4:1 |
| `--matn-2` #C7CFDA → panelda | 10:1 |
| `--siyoh` matn → tilla tugmada | 6.8:1 |

- Matn uchun `rgba(…, .55)` kabi xira qiymatlar **ishlatilmaydi**. Ikkinchi darajali matn faqat `--matn-2` bilan yoziladi.
- Eng kichik matn 13px. Istisno: grafik o'qidagi yozuvlar, ular 12px bo'lishi mumkin.

---

## 3. Fon

Ichki sahifalardagi fon (`PlatformaFon.jsx`) **qasr rasmi va harf yomg'irisiz** bo'ladi. Ular faqat bosh sahifa va kirish ekranida qoladi. Ish ekranida rasm matn kontrastini o'zgartirib yuboradi.

```css
.platforma-fon {
  background:
    radial-gradient(ellipse 70% 40% at 50% 0%, rgba(228,193,150,.20), transparent 70%),
    radial-gradient(ellipse 60% 50% at 50% 110%, rgba(47,73,110,.55), transparent 70%),
    var(--tun);
}
```

- Kirish ekrani (`Kirish.jsx`) eski fonni (rasm va yomg'ir) saqlab qolishi mumkin. Buni `PlatformaFon` ga `bezak` prop berib hal qiling.
- Rahbar dashbordida pastki o'ng burchakda katta **konturli «LIBOSA»** yozuvi turadi:
  - `-webkit-text-stroke: 1px rgba(228,193,150,.16)`, `color: transparent`;
  - `aria-hidden`;
  - faqat ≥768px ekranda ko'rinadi.

---

## 4. Shriftlar

- `index.html` da Forum, Cormorant Garamond (kursiv) va Manrope allaqachon yuklanadi.
- `body` uchun `font-family: var(--sans)` qo'ying. Hozir system-ui turibdi.

| Element | Uslub |
|---|---|
| Sahifa sarlavhasi `h1` / `h2` | `var(--serif)`, 400, 30–40px |
| Bo'lim sarlavhasi `h3` | Manrope 600, 17–18px |
| Kursiv urg'u | `var(--kursiv)` italic, `color: var(--tilla)`, 18–22px |
| Katta raqam (foyda, qoldiq) | Forum yoki Manrope 700, `font-variant-numeric: tabular-nums` |
| Pul summasi | doim ming ajratgich bilan (`1 500 000`) |

- **Kursiv urg'u** faqat bitta qisqa iborada ishlatiladi: «Xayrli tong,», mijoz ismi, «17–19 noyabr uchun 31 ta bo'sh». Butun matnni kursiv qilmang.
- **Tabular raqamlar** barcha pul ustunlariga ham qo'llanadi.

---

## 5. Komponentlar (mavjud sinflarni qayta uslublash)

| Komponent | Sinf | Uslub |
|---|---|---|
| Panel / karta | `.blok`, `.kpi`, `.qator-btn`, `.liboslar li`, `.tasdiq` | `background: var(--shisha); border: 1px solid var(--shisha-chet); border-radius: var(--r-panel); backdrop-filter: blur(14px)` |
| Tanlangan karta | `.tanlandi`, faol | `border-color: var(--shisha-chet-faol)` + `box-shadow: 0 0 0 1px var(--tilla)` |
| Asosiy tugma | `button` | balandlik 54px (telefonda 52px), `border-radius: 999px`, `background: linear-gradient(110deg, var(--tilla-toq), var(--tilla))`, `color: var(--siyoh)`, 700, `box-shadow: 0 8px 28px -10px rgba(228,193,150,.7)` |
| Ikkinchi darajali tugma | `button.ikkinchi` | 46px, pill, shaffof fon, `border: 1px solid rgba(228,193,150,.55)`, `color: var(--oq)` |
| Matnli tugma | yangi `.havola-tugma` | fonsiz, `color: var(--tilla)`, 600. Masalan, «Boshqa amallar (7)» |
| Xavfli tugma | `.xavfli` | shaffof, `color: var(--xavf)`, chegara `rgba(255,155,146,.45)`. Bosilganda **doim tasdiq oynasi** chiqadi |
| Chip / filtr | `.chiplar button`, `.segment button` | 38–40px pill. Faol: `background: rgba(228,193,150,.16)`, chegara `--tilla` |
| Maydon | `input`, `select` | 48px, `border-radius: 14px`, fon `rgba(7,12,22,.6)`, chegara `rgba(228,193,150,.28)`. Fokusda 2px `--tilla-toq` + `0 0 0 4px rgba(204,152,102,.25)` |
| Holat yorlig'i | yangi `.holat` | 26px pill, 13px/600, ranglar 6-bo'limda |
| Ogohlantirish | `.ogohlantirish` | panel + `border-color: rgba(255,138,128,.45)`, sarlavha `--xavf` |
| Ma'lumot matni | `.malumot` | `color: var(--matn-2)` (hozir tilla, bu xato: tilla faqat urg'u uchun) |
| Skelet | `.dashbord-skelet` | barcha «Yuklanmoqda…» matnlari o'rniga shu skelet ishlatilsin |

**Bitta ekranda faqat bitta tilla (asosiy) tugma bo'ladi.** Qolgan amallar ikkinchi darajali yoki matnli tugma bilan ko'rsatiladi.

Tegish maydoni kamida 44×44px. Ikonka bilangina ko'rsatilgan tugmalarga `aria-label` qo'ying.

---

## 6. Holat ranglari (zakaz)

| Holat | Uslub |
|---|---|
| Vaqtinchalik | `border: 1px dashed var(--ogoh)`, matn `--ogoh`, yonida «· N soat qoldi» |
| Bron | `background: rgba(228,193,150,.18)`, matn `--tilla` |
| Berildi | `background: rgba(141,180,232,.16)`, matn `--ber` |
| Qaytarildi | `background: rgba(126,214,160,.16)`, matn `--yaxshi` |
| Kechikdi / qarz | `background: rgba(255,155,146,.16)`, matn `--xavf` |

Zakaz kartasi tepasida **4 bo'lakli holat chizig'i** turadi: 4px balandlik, o'tilgan qadamlar `--tilla`, qolganlari `rgba(251,246,238,.18)`. Ostida qadam nomlari 12px yozuv bilan beriladi.

---

## 7. Maket va navigatsiya

| Ekran | Navigatsiya | Kontent kengligi |
|---|---|---|
| Telefon (<768px) | **Pastki tab-bar** (shisha pill, 64px): Bosh · Bandlik · **＋** (46px yumaloq tilla, Yangi zakaz) · Zakazlar · Ko'proq. Gamburger faqat «Ko'proq» ichida qoladi. | 100%, 16px chet |
| Planshet (768–1199px) | Chapda 80px ikonka paneli. Yangi zakaz tugmasi tilla rangda. | 900px gacha |
| Kompyuter (≥1200px) | Chapda 240px matnli panel: faol element `background: rgba(228,193,150,.16)` + `color: var(--tilla)`. Boshlash progressi shu panelda. | 1180px gacha |

- Ichki bo'limlar (Kassa: Hisobot / Xarajat / …, Katalog, Mijozlar, Hisobotlar) **sahifaning tepasida segment** ko'rinishida ham chiqadi. Hozir ular telefonda faqat menyu ichida yashiringan.
- `main { max-width: 480px }` cheklovi olib tashlanadi. Kengliklar yuqoridagi jadvalga mos bo'ladi.

---

## 8. Ekranlar (ustuvorlik tartibida)

### 8.1 Zakaz kartasi
**Fayl:** `pages/Zakazlar.jsx`, `Karta`.

1. **Shapka:** «‹», `Zakaz #raqam` (Forum 24px), o'ngda holat yorlig'i.
2. **Holat chizig'i.**
3. **Asosiy panel:**
   - mijoz ismi kursivda, ostida libos va sana («17–19 noyabr» ko'rinishida);
   - chiziq;
   - «Qoldiq» va katta summa (34px, tabular).
4. **Bitta asosiy tugma, holatga qarab:**

   | Holat | Tugma |
   |---|---|
   | vaqtinchalik | Avans qabul qilish |
   | bron va qoldiq > 0 | Qoldiqni qabul qilish |
   | bron va qoldiq = 0 | Libosni berish |
   | berildi | Qaytarib olish |
   | qaytarildi va qarz bor | Qarzni yopish |

5. Ikkita ikkinchi darajali tugma: Chegirma, Shartnoma.
6. «Boshqa amallar (N)». Ichida qolgan `<details>` bloklari turadi.
7. **To'lov oynasi.** To'lov formasi pastdan chiqadigan oyna (bottom sheet) bo'ladi:
   - summa maydoni katta (24px);
   - tez chiplar: «Qoldiq to'liq», «Yarmi»;
   - usul tanlash 4 ta segment tugma bilan, `select` emas;
   - tugma matnida summa bo'ladi: «1 500 000 so'm qabul qilish».

### 8.2 Yangi zakaz
**Fayl:** `pages/YangiZakaz.jsx`.

1. 3 qadam: **Sana → Libos → Mijoz va tasdiq**. Tepada «2 / 3» va qadam nomi turadi.
2. Liboslar telefon raqamisiz ham ko'rinadi. Telefon 3-qadamda so'raladi. Qulf (`qulf()`) chaqiruvi «Qo'shish» bosilganda bajariladi, bu hozir ham shunday.
3. Sanalar to'ldirilishi bilan ro'yxat o'zi yangilanadi. «Liboslarni ko'rsatish» tugmasi olib tashlanadi.
4. Liboslar rasmli grid kartalarda ko'rsatiladi: telefonda 2 ustun, planshetda 3–4 ustun. Tanlangan karta tilla chegarali bo'ladi va burchagida ✓ belgisi turadi.
5. Pastda yopishib turadigan panel: tanlanganlar, jami summa va tilla «Davom etish» tugmasi. Planshetda bu panel o'ng tomonda 300px ustun bo'ladi.
6. Qoralama `sessionStorage` da saqlanadi. Harakatsizlik tufayli chiqib ketishdan 30 soniya oldin «Davom etyapsizmi?» oynasi chiqadi.

### 8.3 Rahbar dashbordi
**Fayllar:** `pages/Dashbord.jsx`, `components/DashbordYon.jsx`.

1. **Salomlashish:** «Xayrli tong,» kursivda, ism Forum 40px bilan.
2. **Asosiy panel:**
   - «Sof foyda, [oy]»;
   - summa Forum 56px, `--tilla` rangida;
   - ▲/▼ va o'tgan oyga nisbatan foiz;
   - progress chizig'i: tushgan qism tilla gradient, kutilayotgan qism bo'sh;
   - ostida «X mln tushdi · Y mln kutilmoqda».
3. **3 ta KPI:** Bugun tushum, Bandlik, Zakazlar.
4. **«Diqqat talab» paneli.** Har qator bosiladi va tegishli bo'limga olib boradi.
5. **Takrorlarni olib tashlang.** Hozir «Bugun tushum» ikki joyda bor, `BugunXulosa` esa Hisobotlarda takrorlanadi.

### 8.4 Barcha ichki sahifalar: kompyuter, planshet, telefon

Har sahifa uch o'lchamda ishlashi shart:
- **K** = kompyuter (≥1200px);
- **P** = planshet (768–1199px);
- **T** = telefon (<768px).

Navigatsiya 7-bo'limdagidek: K da matnli chap panel, P da ikonka paneli, T da pastki tab-bar.

| Sahifa (fayl) | Kompyuter (K) | Planshet (P) | Telefon (T) |
|---|---|---|---|
| **Kirish** (`Kirish.jsx`) | Markazda 440px shisha panel. Bezakli fon (qasr va yomg'ir) qoladi. Xodimlar 3 ustunli kartalar ko'rinishida, har kartada bosh harf. | 2 ustunli xodim kartalari, 3×4 PIN klaviatura (tugmalar 72px). | 1 ustun, PIN klaviatura butun kenglikda. PIN 4–6 raqam terilganda o'zi yuboriladi. |
| **Rahbar dashbordi** (`Dashbord.jsx`, `DashbordYon.jsx`) | Asosiy foyda paneli butun kenglikda. Ostida 4 KPI bir qatorda. Keyin 2 ustun: «Diqqat talab» va 6 oylik grafik. Konturli «LIBOSA» yozuvi shu yerda. | Foyda paneli, 2×2 KPI, ostida «Diqqat talab» va grafik ketma-ket. | Foyda paneli, 2×2 KPI (raqamlar 22px), «Diqqat talab», grafik. Davr segmenti sarlavha ostida turadi. |
| **Bosh** (`BoshEkran.jsx`) | Tepada 3 hisoblagich (Olib ketiladi / Qaytariladi / Kechikkan). Ostida 3 ustun ro'yxat. «Yangi zakaz» tugmasi sarlavha qatorida. | Hisoblagichlar bir qatorda, ro'yxatlar 2 ustunda. | Hisoblagichlar gorizontal scroll chiplar ko'rinishida. Ro'yxatlar ustma-ust. «Yangi zakaz» tab-bardagi ＋ tugmasi. |
| **Yangi zakaz** (`YangiZakaz.jsx`, `Vitrina`, `Manekin`) | Qadamlar tepada. Liboslar 4 ustunli grid, o'ngda 320px jami paneli. | Liboslar 3 ustunli grid, o'ngda 300px jami paneli. | Liboslar 2 ustunli grid. Jami paneli pastda yopishib turadi (tab-bar ustida). Qadamlar «2 / 3» ko'rinishida. |
| **Zakazlar ro'yxati** (`Zakazlar.jsx`) | Jadval: raqam, mijoz, libos, sana, holat yorlig'i, summa. Tepada qidiruv va holat chiplari. Qator bosilsa, karta o'ng tomonda 440px panelda ochiladi (ro'yxat ko'rinib turadi). | Ro'yxat kartalar ko'rinishida. Karta bosilsa, alohida sahifada ochiladi. | Kartalar sana bo'yicha guruhlangan (Bugun / Ertaga / Shu hafta). Qidiruv yopishib turadi. |
| **Zakaz kartasi** (`Zakazlar.jsx`, `Karta`, `Hujjat`) | 2 ustun: chapda ma'lumot va to'lovlar tarixi, o'ngda asosiy amal va «Boshqa amallar». To'lov o'ng paneldagi oynada ochiladi. | 2 ustun (60/40). | 1 ustun, 8.1 dagidek. To'lov pastdan chiqadigan oynada. |
| **Mijozlar** (`Mijozlar.jsx`, `Salonchilar.jsx`, `Promokodlar.jsx`) | Tepada segment: Mijozlar / Salonchilar / Promokodlar. Chapda ro'yxat, o'ngda tanlangan mijoz tafsiloti (tarix, o'lchamlar). | Ro'yxat to'liq kenglikda, tafsilot alohida sahifada. | Kartalar. Telefon raqami bosilsa, qo'ng'iroq qilinadi. Segment gorizontal scroll bo'ladi. |
| **Bandlik** (`Kalendar.jsx`) | Hafta yoki oy jadvali. Chap ustun (libos nomi) yopishib turadi. Tepada qidiruv va kategoriya chiplari. Katak bosilsa, o'ng panel ochiladi: bo'sh bo'lsa «Shu libos bilan zakaz», band bo'lsa zakaz qisqachasi. | Hafta ko'rinishi, jadval gorizontal scroll bo'ladi. | Kun yoki 3 kun ko'rinishi. Libos tanlansa, oylik mini-kalendar ochiladi. Tafsilot pastdan chiqadigan oynada. |
| **Katalog** (`Katalog.jsx`, `AksessuarBolimi.jsx`, `RasmBlok`, `TamirBlok`, `MavsumiyNarx`) | Segment: Liboslar / Aksessuarlar. 5 ustunli rasmli grid, filtr chap tomonda 240px. Libos tahriri o'ng panelda ochiladi. | 3 ustunli grid, filtr tepada chiplar ko'rinishida. | 2 ustunli grid. Filtr «Filtr» tugmasi bosilganda pastdan chiqadi. Tahrir alohida sahifada. |
| **Kassa** (`Kassa.jsx`, `Xarajatlar`) | Tepada smena holati paneli (ochiq/yopiq, naqd qoldiq). Segment: Hisobot / Xarajat / Inkassatsiya / Zaloglar / Chiqish / Yopish / Tarix. Mazmun 2 ustunda. | Segment gorizontal scroll, mazmun 1 ustun. | Smena paneli yopishib turadi. Amallar katta tugmalar bilan. «Smenani yopish» tasdiq oynasi bilan. |
| **Hisobotlar** (`Hisobotlar.jsx`, `OylikGrafik`) | Segment: Hisobot / Foyda va zarar / Bildirishnomalar / Grafik. Hisobotlar ro'yxati kartalarda (nom va bir jumla izoh). Davr chiplari faol holatni ko'rsatadi. Jadval to'liq. Foyda va zarar «sharshara» ko'rinishida. | Jadval gorizontal scroll bo'ladi, birinchi ustun yopishib turadi. | Jadval qatorlari kartaga aylanadi. Grafik butun kenglikda. «Oyni yopish» tasdiq oynasi bilan. |
| **Sozlamalar** (`Sozlamalar.jsx`, `Integratsiyalar`, `TelegramBlok`, `TayyorChegirmalar`) | Chapda bo'limlar ro'yxati (hozirgi `SOZLAMA_BOLIMLAR`), o'ngda forma (720px gacha). | Bo'limlar tepada segment, forma to'liq kenglikda. | Bo'limlar ro'yxati alohida ekran. Bo'lim tanlansa, forma ochiladi, «‹ Sozlamalar» orqali qaytiladi. |
| **Platforma paneli** (`Platforma.jsx`, `#platforma`) | Chap panel: Salonlar / Tariflar / So'rovlar / Telegram. Salonlar jadvali, tanlangan salon o'ng panelda. | Jadval kartalarga aylanadi. | Kartalar. Har salon alohida sahifada. |
| **Oflayn** (`Oflayn.jsx`) | Tepada sariq banner «Internet yo'q: faqat ko'rish», ostida keshdagi ro'yxatlar. | Xuddi shunday. | Banner yopishib turadi. |
| **Modallar** (`Vitrina`, `Hujjat`, `Manekin`, tasdiq oynasi) | Markazda shisha oyna (560px gacha), orqa fon `rgba(6,10,18,.6)`. Vitrina to'liq ekranda. | Xuddi shunday. | Pastdan chiqadigan oyna (bottom sheet). Vitrina va Hujjat to'liq ekranda. |

**Umumiy talablar:**
- Bo'sh holatlarda doim amal tugmasi bo'ladi. Masalan: «Hali libos yo'q → Birinchi libosni qo'shish».
- Xatolarda «Qayta urinish» tugmasi bo'ladi.
- Xavfli amallar (bekor qilish, oyni yopish, smenani yopish) **tasdiq oynasi** bilan bajariladi. Oynada natija aytiladi: «Zakaz #124 bekor qilinadi, 450 000 so'm qaytariladi».
- Rahbar uchun «Boshlash» progressi: K da chap panelda, P va T da dashbord tepasida.
- Sinovdan qolgan kunlar shapkada chip bilan ko'rsatiladi.

---

## 9. Harakat (animatsiya)

- Panel paydo bo'lishi: `opacity` va `translateY(8px)`, 200ms, `cubic-bezier(.2,.8,.2,1)`.
- Tugmaga bosilganda `transform: scale(.98)`.
- Tilla tugmalarga sekin aylanadigan nur effektini faqat hover'da qo'shish mumkin.
- `@media (prefers-reduced-motion: reduce)` bo'lsa, barcha animatsiyalar o'chadi.
- Ish ekranlarida zarralar, yomg'ir, WebGL va video **bo'lmaydi**.

---

## 10. Tekshirish ro'yxati (har ekran uchun)

- [ ] Fonda rasm yo'q, matn har joyda bir xil o'qiladi.
- [ ] Ekranda bitta tilla tugma bor.
- [ ] Ikkinchi darajali matn `--matn-2` rangida, 13px dan kichik matn yo'q.
- [ ] Pul summalari tabular va ming ajratgichli.
- [ ] Kompyuter (1280px va 1440px), planshet (820px, tik va yotiq 1180px) va telefon (390px va 360px) kengligida tekshirilgan. Sahifaning o'zida gorizontal scroll yo'q (faqat jadval ichida bo'lishi mumkin).
- [ ] Tab-bar telefonda ko'rinadi, ichki bo'limlar sahifa tepasida turadi.
- [ ] Klaviatura fokusi (tilla halqa) ko'rinadi, ikonkali tugmalarda `aria-label` bor.
- [ ] Xavfli amalda tasdiq oynasi chiqadi.
- [ ] `npm run build` xatosiz o'tadi, `PROGRESS.md` yangilangan.

## 11. Bajarish tartibi

1. Tokenlar va fon (2, 3, 4).
2. Komponentlar (5, 6).
3. Navigatsiya (7).
4. Zakaz kartasi, Yangi zakaz, Dashbord (8.1–8.3).
5. Qolgan ekranlar (8.4).

Har bosqichdan keyin foydalanuvchiga skrinshot ko'rsatib tasdiq oling, so'ng keyingisiga o'ting.
