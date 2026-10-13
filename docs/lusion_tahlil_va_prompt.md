# lusion.co/about tahlili va Weddy uchun prompt

Sana: 2026-10-10. Manbalar: sahifaning matni (to'liq o'qildi), Awwwards'dagi Lusion ish tahlili (case study), Awwwards teglari.
**Cheklov:** bu sessiya tarmog'i lusion.co ni brauzerda ochishga ruxsat bermadi, shuning uchun animatsiyalarni o'z ko'zim bilan ko'rmadim. Quyida
"(xulosa)" deb belgilangan joylar matn tuzilmasi, case study va Awwwards teglaridan chiqarilgan xulosa, kuzatuv emas.

## 1. Sahifa tuzilmasi (boshidan oxirigacha)

| # | Bo'lim | Nima bor | Effekt (manba yoki xulosa) |
|---|---|---|---|
| 1 | Shapka | Logo, "back", "Let's talk" (email), Menu/Close tugmasi | To'liq ekranli menyu ochiladi (xulosa: matn "Menu / Close" almashadi) |
| 2 | Hero | "SCROLL TO EXPLORE", katta sarlavha "We are a creative production studio crafting unique digital experiences", qisqa kirish | Ulkan matn qatorma-qator ochiladi, fonda interaktiv 3D (xulosa) |
| 3 | Asoschi | "001" raqami, ism va lavozim, paragraf, "Swipe to change" | Suriladigan karusel, kartalar almashadi |
| 4 | Brendlar | Kirish gapi, ~15 brend logotipi qatorlari | Har qator takrorlanadi: cheksiz aylanadigan lenta (marquee) |
| 5 | Mukofotlar | Jami 58, Awwwards/FWA/CSSDA/Webby bo'yicha sonlar | Raqamlar sanab chiqadi (pastki paneldagi "0" hisoblagichlar, xulosa) |
| 6 | Maqolalar (3) va Chiqishlar (5) | Ro'yxat: nom, joy, sana | Qatorlar ustiga kelganda ajraladi (xulosa) |
| 7 | Mutaxassislik | 4 ustun: Strategy, Creative, Tech, Production, har birida harf belgisi (s, c, t, P) va xizmatlar ro'yxati | Ustunlar navbatma-navbat chiqadi |
| 8 | Chaqiriq | "Is your big idea ready to go wild?", "Let's work together!", "Continue to scroll" | Katta tipografiya, keyingi sahifaga o'tishga undaydi |
| 9 | Oyoq | Manzil, ijtimoiy tarmoqlar, ikki email, obuna, R&D havolasi | Oddiy |
| 10 | Pastki panel | "Keep scrolling", "Our projects", "Next page", PLAY / MUTE | Doimiy panel: ovoz yoqish/o'chirish, keyingi sahifaga o'tish |

## 2. Lusion uslubining asosiy tamoyillari

1. **Hamma narsani real vaqtda hisoblamaslik.** Case study'dagi asosiy g'oya: "You don't need to do everything real-time".
   - Mato simulyatsiyasi Houdini'da oldindan hisoblanadi va ~220 KB ArrayBuffer qilib saqlanadi.
   - Sahna Redshift'da video qilib render qilinadi, ustiga faqat yorug'lik va kamera harakati real vaqtda qo'shiladi.
   - Haykal oldindan pishirilgan normal/AO/thickness xaritalari va matcap orqali "shaffof" ko'rinadi.
2. **Vertex animation.** Kiyim harakati PNG teksturalarga yoziladi (pozitsiya + normal), shader kadrni sichqonchaga qarab tanlaydi.
   - 11 ta kalit kadr va 16-bitli kodlash ishlatiladi.
   - Hajmi: kompyuterda 4096 uch ~983 KB, telefonda 1024 uch ~246 KB.
3. **Kursorga javob beruvchi sahna.** Yorug'lik kursorga ergashadi, kamera ~2° buriladi, obyekt sichqonchaga qarab egiladi.
4. **Aylantirishga bog'langan hikoya.** Har bo'lim alohida "kadr" sifatida ishlaydi, pastki panel doim keyingi qadamni ko'rsatadi.
5. **Toza tipografiya.** Ulkan sarlavhalar va ko'p bo'sh joy, kam rang. Meta-teglarda faqat oq rang ko'rinadi, ya'ni yorug' fon (xulosa).
6. **Ovoz ixtiyoriy.** PLAY/MUTE bor, lekin standart holatda o'chiq.
7. **Arxitektura.** Sayt to'liq statik, three.js asosida.

## 3. Weddy uchun tayyor prompt

Quyidagini AI dasturlash yordamchisiga (Antigravity, Claude Code va h.k.) bering:

```text
Loyiha: F:\Project_Antigravity\weddy. Avval PROGRESS.md ni o'qi. Bosh sahifa frontend/src/pages/Reklama.jsx, reklama.css,
reklamaSahna.js va ezazBelgi.js da. Bu sahifa — Weddy (kelin liboslari salonlari uchun ijara tizimi) taqdimoti.

VAZIFA: Mavjud bosh sahifani lusion.co/about darajasidagi, kuchli effektli "kinematik" sahifaga aylantir.
Hozirgi kontent, formalar (ArizaForma → tenants.Ariza), WebGL zarracha sahnalari va bosh kadr videosi saqlanadi.

QATTIQ QOIDALAR
- React 19 + Vite, oddiy CSS, router yo'q. Yangi kutubxona faqat zarur bo'lsa: three.js ga ruxsat, boshqasi so'ralsin.
- Brend: nomi Weddy. Logotip, ranglar va shriftlar EZAZ'dan:
  - logotip: EZAZ malika belgisi (ezazBelgi.js);
  - ranglar: tilla #CC9866 va to'q ko'k #2F496E;
  - shriftlar: sarlavha Forum (Casagrande Deco o'rnida), urg'u Cormorant Garamond kursiv, matn Manrope.
- Barcha UI matnlari va izohlar o'zbek tilida (lotin).
- prefers-reduced-motion: hamma harakat o'chadi, kontent darhol ko'rinadi.
- WebGL bo'lmasa, sahifa oddiy fon bilan to'liq ishlaydi.
- 60 fps maqsad. Telefonda zarracha va vertex soni 4 barobar kam. Ko'rinmayotgan sahna chizilmaydi.
- Oxirida npm run lint va npm run build o'tsin. Commit qilma. PROGRESS.md ning 42-qism yozuvini yangila.

SAHIFA TUZILMASI (har biri to'liq ekranli "kadr")
1. Shapka.
   - Chapda logo, o'ngda "Bog'lanish" va Menyu/Yopish tugmasi.
   - Menyu to'liq ekranda ochiladi: havolalar katta shriftda, qatorma-qator pastdan ko'tariladi (clip-path + translateY, 90 ms stagger).
2. Hero.
   - "Pastga aylantiring" belgisi.
   - Ulkan sarlavha: "Har bir libos qayerda, kimda va qachon qaytadi". Qatorlar niqob ichidan ko'tariladi.
   - Fonda mavjud video + zarracha libos.
   - Kursor yaqinlashganda: libos yengil egiladi, tilla nur kursorga ergashadi, kamera ±2° buriladi.
3. "001 — Salon egasi" karuseli.
   - Uch rol: Rahbar, Sotuvchi, Salonchi. Har birida raqam, rol nomi va 2–3 gap.
   - Sichqoncha bilan sudrab yoki surib almashtiriladi. Inersiya bor, chetga yetganda qaytib turadi.
   - "Surib almashtiring" belgisi.
4. Lenta.
   - Uch qator cheksiz yuguruvchi so'zlar: BRON · ZAKAZ · ZALOG · KASSA · KATALOG · FOYDA.
   - Qatorlar qarama-qarshi yo'nalishda harakatlanadi.
   - Aylantirish tezligiga qarab tezlashadi va qiyshayadi (skewX, maksimal 8°).
5. Raqamlar.
   - Masalan: "8 modul", "16 hisobot", "3 rol", "14 kun bepul".
   - Ekranga kirganda 0 dan sanaladi (1.2 s, easeOutExpo), tabular raqamlar.
6. Imkoniyatlar: 4 ustun (Lusion'dagi Strategy/Creative/Tech/Production kabi).
   - B — Bron va kalendar, Z — Zakaz va zalog, K — Kassa va smena, H — Hisobot va foyda.
   - Katta harf belgisi tilla konturda, ostida ro'yxat. Ustunlar navbatma-navbat ochiladi.
   - Ustiga kelganda harf 3D'da aylanadi (CSS perspective).
7. "Qanday ishlaydi".
   - Mavjud 4 qadam saqlanadi, tilla ip aylantirishga qarab tikiladi.
8. Chaqiriq.
   - Ulkan matn: "Saloningiz Weddy'ga tayyormi?". Har harf kursor yaqinida biroz ko'tariladi (magnit effekti).
   - "A'zo bo'lish" tugmasi magnitli: kursorga 12 px gacha tortiladi.
9. A'zo bo'lish va Bog'lanish formalari (mavjudi saqlanadi), oyoq.
10. Doimiy pastki panel.
   - Chapda "Pastga aylantiring" va jami progress chizig'i.
   - O'rtada joriy bo'lim nomi, almashganda matn yuqoriga sirg'anadi.
   - O'ngda OVOZ tugmasi: standart o'chiq. Yoqilsa, WebAudio'da sintez qilingan yumshoq pad va tugma ustida kichik tilla "chink" ovozi.

EFFEKTLAR
- Silliq aylantirish:
  - lerp 0.08 bilan o'zimiz yozgan smooth scroll; native scroll saqlanadi, transform bilan.
  - Klaviatura, sichqoncha g'ildiragi va teginish ishlashi shart.
  - Anchor havolalar ham ishlasin.
- Kursor: 3 holat.
  - Oddiy holat: kichik nuqta + ergashuvchi halqa.
  - Havola yoki tugma ustida: halqa kattalashadi.
  - Karusel ustida: halqa ichida "Suring" yozuvi.
  - Teginishli qurilmalarda kursor yo'q.
- Bo'limlar orasida o'tish: kirayotgan bo'lim clip-path bilan ochiladi, chiqayotgani biroz kichrayib xiralashadi.
- Matn ochilishi: sarlavhalar qatorlarga bo'linadi va har qator niqob ichidan ko'tariladi (IntersectionObserver, bir marta).
- Yuklanish: hozirgi foiz + "Xush kelibsiz" darvozasi saqlanadi. Darvoza ochilganda tilla chang tarqaladi.
- "Pishirilgan" 3D (Lusion tamoyili):
  - og'ir simulyatsiya brauzerda hisoblanmaydi;
  - libos pardasining harakati kerak bo'lsa, oldindan hisoblangan kadrlar teksturadan o'qiladi (vertex animation);
  - aks holda mavjud zarracha tizimi ishlatiladi.

TEKSHIRUV
- Playwright bilan 1440×900, 1280×720 va 390×844 o'lchamlarida har bo'limdan skrinshot ol.
- Konsolda xato bo'lmasin, gorizontal siljish bo'lmasin.
- Menyu va formada klaviatura fokusi ishlasin.
- Reduced-motion rejimini alohida tekshir.
```

## 4. Tavsiyalar
- **Hammasini birdan qilmaslik kerak.** Eng katta ta'sir beradiganlari:
  1. silliq aylantirish va matnning qatorlab ochilishi;
  2. magnitli tugmalar va 3 holatli kursor;
  3. pastki panel va ovoz;
  4. karusel.
- **Mustaqil ekspert tahlilida MVP katta deyilgan edi.** Reklama sahifasi salon tizimining o'zidan oldin turmasligi kerak, shuning uchun
  bu ishni 1–2 kunlik alohida qism qilib berish to'g'ri.
- **Vertex animation qimmat.** U uchun Houdini yoki Blender'da mato simulyatsiyasi kerak. Video va zarrachalar hozircha shu ta'sirning
  ko'p qismini beradi.

Manbalar: [lusion.co/about](https://lusion.co/about/), [Awwwards case study](https://www.awwwards.com/case-study-for-lusion-by-lusion-winner-of-site-of-the-month-may.html), [Lusion v3 — Awwwards](https://www.awwwards.com/sites/lusion-v3), [Codrops maqolasi](https://tympanus.net/codrops/2026/04/13/lusion-where-digital-craft-meets-ambitious-experimentation/).
