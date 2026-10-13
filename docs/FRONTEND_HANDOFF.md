# Weddy bosh sahifasi: frontend topshirig'i (handoff)

Sana: 2026-10-10. Yangi agent ishni shu yerdan davom ettiradi. Avval shu faylni, keyin `PROGRESS.md` ni o'qi.

## Prompt (agentga shu bo'limni bering)

```text
Sen Weddy loyihasining frontendini davom ettirasan. Loyiha: F:\Project_Antigravity\weddy
(Django 5.2 + DRF backend, React 19 + Vite 8 frontend). Avval PROGRESS.md va docs/FRONTEND_HANDOFF.md ni o'qi.
Foydalanuvchi o'zbek tilida (lotin) yozadi: javoblar, UI matnlari va kod izohlari o'zbekcha.

MAHSULOT
- Weddy: kelin liboslari ijara salonlari uchun ko'p salonli platforma. Birinchi mijoz salon EZAZ.
- Bosh manzil "/" kirmagan odamga reklama (taqdimot) sahifasini ko'rsatadi, "/#kirish" esa kirish ekrani.
- "A'zo bo'lish" formasi hisob ochmaydi: so'rov tenants.Ariza ga tushadi.
- Sayt dev rejimda http://localhost:5173 da ishlaydi.

BREND QARORLARI (o'zgartirma, foydalanuvchi aniq aytgan)
- Sayt nomi WEDDY. Logotip, ranglar va shriftlar EZAZ brendidan:
  - logotip: EZAZ malika belgisi, src/pages/ezazBelgi.js (BELGI_D, viewBox 0 0 519.4 562.9);
  - ranglar: tilla #CC9866 (yorug'i #e4c196), to'q ko'k #2F496E, chuqur fon #0e1a2b, fil suyagi #fbf6ee;
  - shriftlar: sarlavha 'Casagrande Deco' → hozircha Forum (Casagrande pullik, veb-litsenziya yo'q),
    urg'u (<em>) Cormorant Garamond kursiv, matn Manrope. Hammasi index.html dagi Google Fonts dan.
- Sahifa "prezentatsiya" kabi bo'lishi kerak: to'liq ekranli sahnalar, kuchli animatsiyalar.

BOSH SAHIFA FAYLLARI
- src/pages/Reklama.jsx:
  - matn sahnalari, aylantirishga bog'liq hisob (--p har sahnaga, --bp bosh sahnaga, --jami);
  - Yuklanish (foiz + "Xush kelibsiz"), Iz (kursor uchqunlari), BoshVideo, ArizaForma;
  - ALOQA bo'sh — to'ldirilmaguncha "Bog'lanish"da faqat forma.
- src/pages/reklama.css: barcha qoidalar .rk ichida. Ranglar :root emas, .rk dagi o'zgaruvchilarda (--tilla, --kok, --siyoh, --serif, --kursiv).
- src/pages/reklamaSahna.js:
  - kutubxonasiz WebGL: atlas foni va zarrachalardan yig'iladigan shakllar (libos → kalendar → uzuklar → grafik → chang → libos);
  - PALITRA — har sahna rangi, KENG/TOR.shaf — zarracha shaffofligi (0-sahnada 0.5, chunki ortida video bor).
- public/video/bosh_keng.* va bosh_tor.*:
  - bosh kadr videosi (Seedance 2.5, 480p qoralama), webm + mp4 + jpg poster, uzluksiz aylana qilib ffmpeg bilan tikilgan;
  - asl fayllar media/artlist/ da;
  - video .rk-video ichida, mix-blend-mode: lighten bilan WebGL ustiga qo'shiladi;
  - bosh sahna chiqib ketganda so'nadi va pause bo'ladi;
  - prefers-reduced-motion da video chiqmaydi.
- Dev konsol yordamchilari: __sahna.darhol(0..5), __hisobla().

QOIDALAR
- Oddiy CSS, router yo'q, yangi kutubxona qo'shishdan oldin foydalanuvchidan so'ra.
- prefers-reduced-motion va WebGL'siz holat ishlashi shart.
- Har o'zgarishdan keyin frontend papkasida npm run lint va npm run build.
  - Sozlamalar.jsx, Katalog.jsx va Platforma.jsx dagi set-state-in-effect ogohlantirishlari eski, sening ishing emas.
- Commit qilma (repoda hali commit yo'q, foydalanuvchi o'zi hal qiladi).
- O'zgarishdan keyin PROGRESS.md dagi 42-qism (reklama bosh sahifasi) yozuvini yangila.
- Foydalanuvchining Artlist (Seedance 2.5) hisobi bor. Har generatsiya kredit sarflaydi: narxini ayt va ruxsat ol.
  - 480p qoralama ~200 kredit/soniya.
  - Qoralamani 1080p ga 2026-10-17 gacha render qilish mumkin.

OCHIQ ISHLAR (foydalanuvchi hali hal qilmagan)
1. Bosh videoni 1080p ga render qilish (narxini aytib ruxsat olish kerak).
2. Telefon videosida (bosh_tor) o'rtadan ko'ndalang yorug' chiziq o'tadi. Uni chiziqsiz qayta yaratish tavsiya qilingan (~2 000 kredit).
3. lusion.co/about uslubidagi kuchaytirish rejasi tayyor: docs/lusion_tahlil_va_prompt.md.
   Tavsiya etilgan tartib:
   1. silliq aylantirish + sarlavhalarning qatorlab ochilishi;
   2. magnitli tugmalar + 3 holatli kursor;
   3. doimiy pastki panel + ovoz;
   4. rollar karuseli.
4. Casagrande Deco veb-litsenziyasi olinsa: faylni public/fonts ga qo'yib, @font-face va .rk dagi --serif ga qo'shish.

TEKSHIRISH
- Sahifani 1440×900 va 390×844 o'lchamlarida brauzerda ko'rib chiq: yuklanish, bosh kadr, 3 kadr, imkoniyatlar,
  qanday ishlaydi, a'zo bo'lish, bog'lanish.
- Konsolda xato bo'lmasin, gorizontal siljish bo'lmasin.
- Yuklanish ekranini qayta ko'rish uchun sessionStorage dagi weddy.reklama_korildi ni o'chir.
```

## Tarix (qisqacha)
- **Birinchi bosqich:** estherwong.fun animatsiyalari asosida bosh sahifa TZ va HTML prototip tayyorlandi. Keyin foydalanuvchi sahifaning
  nomini Weddy qildi va "prezentatsiya kabi" bo'lishini so'radi.
- **Brendga moslash:** foydalanuvchining real sahifasi (Reklama, pushti-binafsha WebGL) EZAZ brendiga o'tkazildi: logotip, ranglar,
  shriftlar va WebGL palitrasi.
- **Bosh kadr videosi:** Seedance 2.5 da ikkita 10 soniyali qoralama yaratildi (4 000 kredit) va bosh kadrga qo'shildi.
- **Lusion tahlili:** lusion.co/about tahlil qilindi va kuchaytirish uchun prompt yozildi.
- **Tarmoq cheklovi:** cloud sessiyadan artlist.io va lusion.co ochilmaydi. Videolarni foydalanuvchi o'zi yuklab olib papkaga qo'ygan.
