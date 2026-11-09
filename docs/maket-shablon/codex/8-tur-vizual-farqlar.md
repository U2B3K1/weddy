O‘lchamlarni **1440 px kenglikka moslab** solishtirdim; maket ranglari taxminiy, bizdagi qiymatlar HTML’dan olindi. 207 px menyu, 99/252/158 bento, kontent tartibi, Manrope va matnli logo saqlanadi. Fayllar o‘zgartirilmadi.

1. **Hero portreti — eng katta farq.** Maketda kelin yuqori qismning o‘ng markazini egallaydi; bizda faqat zal bor. Bella suratidan `360×350px` qatlam yarating: kontentning o‘ngidan taxminan `23%`, tepadan `0`; `object-position:50% 14%`, yorqinlik `1.10`, chap/past chetlarga mask. Bu kesilgan siluet emas, yumshoq qo‘shilgan portret bo‘ladi.

2. **Fon fotosi va so‘nishi.** Maketda iliq lyustra, vertikal qoramtir interyer; bizda yorug‘ gumbaz, yirik arxitektura. Yuqorimiz qorong‘iroq emas, ammo Dashboard’da gradient `.66` ga 55% da, Kassada `.70` ga 50% da yetadi. Qorong‘ilashishni 65–70% gacha kechiktiring; sariq-jigarrang tusni yengil qo‘shing. Boshqa foto bo‘lmasa, aynan interyer mosligi cheklangan qoladi.

3. **Panel materiali.** Maketda shishaning tepasi yorug‘roq, tilla cheti aniqroq; bizdagi `rgba(18,23,34,.84)` deyarli bir xil to‘q yuzaga aylangan. Asosni `.76`, yuqori oq yaltirashni `.10`, chegarani `rgba(236,190,120,.40)` qiling; radius `16px` saqlansin. Keng sariq tashqi nur qo‘shmang.

4. **Kassa tablari.** Maketda umumiy konturli shisha tasma, 22–24 px ikonkalar va faol to‘la tilla tabletka; bizda oddiy matn/tagchiziq. `.tablar`ni `46px` balandlikdagi panelga aylantiring, mavjud oltita bandga SVG qo‘shing; faol matn `#171717`, fon `#F5BD65 → #E9AA50`.

5. **Smena qatori.** Maketda yashil shisha, katta tasdiq doirasi va konturli yopish tugmasi; bizda neytral panel, 8 px nuqta va havola. `.smena`ga yashil gradient/chegara, `.ochiq` oldiga `28px` tasdiq, yopishga quvvat SVG’si va `36px` konturli tugma bering. Barcha mavjud summalar saqlansin.

6. **Hero matni va tugmasi.** Maketda ikki qatorli salom: birinchisi och tilla, ikkinchisi oq; bizda bir qatorli `44px` sarlavha. `Assalomu alaykum,<br>Nodira!`ni Cormorant `600 42px/1.03` qiling. Tugma to‘la sariqdan shaffof qora/tilla konturga o‘tsin, balandligi `36px`; mavjud yordamchi matn saqlansin.

7. **Chap navigatsiya.** Maketda ikonka taxminan `24–26px`, matn `14–15px`, qatorlar `48–50px`; bizda `20/14/44px`. `.nav`ni `48px`, SVG’ni `24px`, matnni `14px/600` qiling; faol fondagi tilla `.22 → .30`, chap chiziq `5px`. Uy, kalendar, libos, odamlar, sozlama ikonkalari tanish siluetlarda bo‘lsin; logo o‘zgarmasin.

8. **Menyuning pastki qismi.** Maketda promo, avatarli foydalanuvchi kartasi va “Chiqish”; bizda katta bo‘shliq, HTML’da bu bloklar yo‘q. Nav’dan keyin `margin-top:auto` footer: `183×155px` portretli promo, `60px` foydalanuvchi kartasi, `44px` chiqish. Promo radiusi `14px`, chegarasi tilla `.45`.

9. **Yuqori panel.** Maket filial/sanada chevron, sanada kalendar, o‘ngda aylana avatar bilan tugaydi; bizda uchta matnli tabletka. Filialga `16px` chevron, sanaga `20px` kalendar qo‘shing; oxirgi tabletkani `42px` avatar, yashil nuqta va chevronga almashtiring. Ism/rol ochiladigan kartada yoki menyu footerida qolsin.

10. **KPI kartalari.** Maketda kattaroq, yorqin ikonka va past-o‘ngda rangli sparkline; bizda `56px` asos ichida atigi `20px` ikonka, faqat bir sparkline bor. SVG `30px`, asos `56px/r20`, fon alfa `.22`; raqam `25 → 26px`, yorliq oqroq. Qarz qizil qoladi; qolgan kartalarga faqat haqiqiy tarix/delta mavjud bo‘lsa grafik qo‘shilsin.

11. **Tushum grafigi.** Maketda summa/delta va ikki qatorli legenda ravshan, har nuqtada halqa, oxirida nur; bizda oldingi summa matni va bitta faol nuqta. `.jami>b`ni `26px`, joriy chiziqni `3px`, nuqtalarni `r=4`, oxirgisini `r=6` va `drop-shadow` qiling; gradient yuqorisi `.45`. Tooltip boshlanishda yashirin, hover/focus’da ochilsin, chiqishda yopilsin.

12. **Libos galereyasi.** Maketda oltin/kumush/bronza medal va alohida qalin narx; bizda uchala medal qora, ijara/qiymat bitta mayda qator. `.orin` fonlari `#F3BF70/#D5D7DE/#C67D49`, matni qoramtir bo‘lsin. Mavjud qiymatni alohida `14px/700` qatorga ajrating; ma’lumotdagi jami summani “ijara narxi” deb qayta nomlamang.

13. **Diqqat ro‘yxati va pastki kartalar.** Maket ro‘yxatida yuzlar va holat tabletkalari; bizda signal ikonkalari/chevron. Mijozga tegishli signalda mavjud avatarni `36px` doira qiling, qurilmada ikonka saqlansin; o‘ngga tegishli sariq/qizil status qo‘shilsin. Pastda kassa summasi `22 → 25px`, halqa `84 → 94px`, legenda soniga foiz; kassaga past-o‘ngda nozik tilla egri bezak bering.

14. **Kassa ro‘yxati.** Maketda jadval sarlavhasi, to‘liq tilla tanlov chegarasi va “Qoldiq” konturi; bizda faqat chap chiziq. Qidiruv ostiga mavjud ustunlarga mos `Zakaz / Libos / Mijoz / Qoldiq` satr qo‘shing. `.tanlandi`ga `1px #F3BF70` to‘liq chegara, radius `13px`; qoldiqni tilla konturli tabletka qiling, qarz tabletkasi qizil bo‘lsin. Uch guruh va bitta qidiruv saqlansin.

15. **Kassa o‘ng paneli.** Serif sarlavha allaqachon yaqin; asosiy farq klaviatura va usullar. Tugmalar hozir `50px`, tekis `.04` fonli: `40–42px`, shrift `24px/500`, yuqori yaltirashli gradient qiling. “To‘lov usuli” yorlig‘i va usullarga SVG qo‘shing, faol fon to‘la tilla bo‘lsin; kvitansiya izohiga `18px` chek ikonkasi, matnga `13px #B7BAC5`.

Quyidagi besh parcha 1–5-bandlar uchun. Dashboard `<main>`iga `dashboard`, Kassanikiga `kassa` klassini qo‘shish kerak. Dashboard’da `.ustki`dan oldin `<img class="hero-portret" src="/_blob/7d80ca195130908ffa9854d230fd9af0" alt="" aria-hidden="true">` joylashtiriladi.

```css
/* 1. Dashboard hero portreti */
.dashboard .hero-portret {
  position: absolute;
  z-index: -2;
  top: 0;
  right: 23%;
  width: 360px;
  height: 350px;
  object-fit: cover;
  object-position: 50% 14%;
  filter: brightness(1.10) saturate(.94);
  pointer-events: none;
  -webkit-mask-image:
    linear-gradient(90deg, transparent, #000 20%, #000 80%, transparent),
    linear-gradient(#000 72%, transparent 100%);
  -webkit-mask-composite: source-in;
  mask-image:
    linear-gradient(90deg, transparent, #000 20%, #000 80%, transparent),
    linear-gradient(#000 72%, transparent 100%);
  mask-composite: intersect;
}

/* 2. Fon: iliqroq, sekinroq so‘nadi */
.mazmun::before {
  z-index: -3;
  height: 520px;
  background:
    linear-gradient(180deg,
      rgba(13,19,32,.28) 0%,
      rgba(13,19,32,.45) 45%,
      rgba(13,19,32,.76) 70%,
      #0D1320 100%),
    linear-gradient(rgba(115,72,32,.10), rgba(115,72,32,.10)),
    url("/_blob/c9a1861df1eef0d758b27417a77833a6")
      center 45% / cover no-repeat;
}

/* 3. Shisha panel retsepti */
.panel {
  border-color: rgba(236,190,120,.40);
  background:
    linear-gradient(145deg, rgba(255,255,255,.10), transparent 62%),
    rgba(18,23,34,.76);
  backdrop-filter: blur(16px) saturate(115%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.13),
    inset 0 -1px 0 rgba(243,191,112,.05),
    0 10px 24px rgba(0,0,0,.27);
}

/* 4. Kassa tablari: har havolaga svg.i qo‘shiladi */
.kassa .tablar {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 46px;
  padding: 4px;
  border: 1px solid rgba(243,191,112,.60);
  border-radius: 14px;
  background:
    linear-gradient(rgba(255,255,255,.07), transparent),
    rgba(16,20,29,.78);
}
.kassa .tablar a {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 10px;
  border-radius: 999px;
  color: #F5F2EE;
  white-space: nowrap;
}
.kassa .tablar a .i { width: 23px; height: 23px; }
.kassa .tablar a.faol {
  color: #171717;
  background: linear-gradient(135deg, #F9C97A, #E9AA50);
  box-shadow:
    inset 0 1px 0 #FFE1A8,
    0 2px 10px rgba(243,191,112,.20);
}

/* 5. Smena: yopish havolasiga quvvat svg.i qo‘shiladi */
.kassa .smena {
  min-height: 48px;
  padding: 8px 16px;
  border-color: rgba(98,212,163,.60);
  background:
    linear-gradient(100deg, rgba(45,145,91,.30), rgba(24,74,53,.16)),
    rgba(15,27,26,.88);
}
.kassa .smena .ochiq { color: #94E8B5; }
.kassa .smena .ochiq::before {
  content: "✓";
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #87E5A6;
  color: #102D20;
  font-size: 21px;
  font-weight: 800;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.40);
}
.kassa .smena a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 18px;
  border: 1px solid #F3BF70;
  border-radius: 999px;
  color: #F5F2EE;
  background: rgba(13,19,25,.42);
  box-shadow: inset 0 0 12px rgba(243,191,112,.09);
}
```