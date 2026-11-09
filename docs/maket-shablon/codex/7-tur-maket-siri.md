“Siri” — **iliq salon fotosi, sovuq qorong‘i panellar, yorqin qirralar va zich bento kompozitsiyasi** birgalikda ishlashida. Hashamat faqat tilladan kelmaydi: katta libos suratlari, serif sarlavhalar va turli enli bloklar uni kuchaytiradi. Bu ko‘rinish qorong‘i glassmorphism’ga yaqin; Apple Liquid Glass’iga xos optik sinish dalili rasmlarda ko‘rinmaydi. Sizning shabloningiz materialni qisman olgan, ammo kompozitsiya, zichlik va suratlarning ta’siri ancha boshqacha.

**O‘lchov chegarasi:** geometriya PNG koordinatalaridan, ranglar piksellardan olindi. Asl shrift, `rgba`, blur va qatlamlar PNG’dan tiklanmaydi; ular uchun quyida qayta yaratish retsepti berilgan. 1–3-rasmlar uchun masshtab `1440/1672 ≈ 0.861`; 4-rasm aslida **1586×992**.

1. **Material**

Apple Liquid Glass fonni sindiradi, atrof yorug‘ligini aks ettiradi va chetlarda linza ta’sirini yaratadi. Bu maketlarda esa yumshoq rang o‘tishlari va yaltiragan konturlar ustun. Statik PNG animatsiya yoki haqiqiy refraksiyani isbotlamaydi. [Apple tavsifi](https://developer.apple.com/videos/play/wwdc2025/219/)

Dashboard panelining yuqorisida o‘lchangan rang `#24252C`, grafik ichida `#161B24`; demak, sirt bir tekis emas. Mos retsept:

- Asos: `rgba(18,23,34,.84)`, ustiga oqning `.06 → 0` gradienti.
- `backdrop-filter: blur(16px) saturate(115%)`.
- Chegara `1px rgba(236,190,120,.30)`, yuqorida ichki oq yorug‘lik `.10`.
- Soya `0 12px 28px rgba(0,0,0,.25)`.
- Radius: manbada taxminan `18–20px`, 1440 ekranida `16–17px`.

2. **Fon**

Ko‘rinadigan foto tafsiloti asosan yuqori **300–430 manba px** ichida; pastda qorong‘i ko‘kimtir maydon hukmron. Suratning asl balandligini aniqlab bo‘lmaydi: to‘liq foto ustidagi gradient ham shu natijani beradi.

Qayta yaratish: foto qatlamini `height:520px`, `background-size:cover` qiling; ustiga markazi ochiq vinyetka va vertikal qorong‘ilashish qo‘ying. Dashboardda kelin KPI ortigacha tushadi; qolgan ekranlarda lyustra va liboslar yuqorini bezaydi. Panel ortidan **foto shakllaridan ko‘ra iliq rang dog‘lari** seziladi. `.84` opacity fon hissasini taxminan 16% qoldiradi; bu o‘lchangan shaffoflik emas.

3. **Joylashuv**

Dashboard koordinatalari, taxminan ±3 manba px:

| Qism | PNG → 1440 ekran |
|---|---|
| Chap menyu | 240 → 207 px |
| Kontent boshlanishi | x262 → x226 |
| Kontent eni | 1391 → 1198 px |
| Kartalar oralig‘i | 14–18 → 12–16 px |
| KPI qatori | y297, h115 → y256, h99 |
| O‘rta qator | y428, h293 → y369, h252 |
| Pastki qator | y734, h183 → y632, h158 |

Bu masonry emas: **har qatorning yuqori-pastki chizig‘i tekis**, qatorlar balandligi esa har xil.

- KPI: to‘rtta deyarli teng karta; generatsiya sabab enlari aynan teng emas.
- O‘rta qator: grafik **590px**, galereya **446px**, ro‘yxat **325px**. 12 ustunli tizimda **5/4/3** yaqinlashtirish mos.
- Pastda: to‘rtta taxminan teng karta.
- Sotuvchi ekranida: yuqorida uch vazifa bloki, pastda ikki keng blok.
- Zakazlarda: katta jadval + tor “Bugun” ustuni.
- Kassada: taxminan **63/37** nisbatli ro‘yxat va to‘lov paneli.

Sarlavha retsepti: ikonka + nom, qolgan bo‘shliq, son yoki “Barchasi →”. Katta vazifa bloklarida ikonka tagligi bor; grafik va kichik panellarda oddiy ikonka ishlatilgan.

4. **Tipografiya**

Vizual yaqinlik: katta sarlavhalarga **Cormorant Garamond 500–600**, interfeysga **Roboto Condensed 400–600**. Bu aniqlangan original shriftlar emas.

1440 ekran uchun shkala: H1 **40–44px**, katta vazifa sarlavhasi **25–28px**, oddiy blok nomi **17–19px**, KPI **25–28px/700**, asosiy matn **14–16px**, yordamchi matn **11–13px**. Serif asosan kayfiyat beradi; jadval va KPI raqamlari sans-serif bo‘lgani uchun tez o‘qiladi.

5. **Rang**

Yaqin palitra: fon `#0D1320`, panel `#191E29`, matn `#F5F2EE`, ikkilamchi `#B7BAC5`, tilla `#F3BF70`; ko‘k `#79A9F2`, yashil `#62D4A3`, pushti `#D97BAA`, binafsha `#BD8DE1`, qizil `#F08089`.

Ranglar takroriy joylarda — ikonka tagligi, badge, sparkline — guruh yaratadi. Lekin barcha KPI va statuslarni ranglash chalg‘itishi mumkin: ayniqsa “Bron” ma’nosi ekranlar orasida tilla/yashil almashsa. Semantik ranglarni qat’iylashtirish kerak.

6. **Komponent retseptlari**

- KPI: 56px ikonka tagligi, ikki-uch satr, yuqori o‘ngda delta; pastki o‘ngda gradient bilan to‘ldirilgan SVG sparkline.
- Ro‘yxat: 40–48px avatar + ism/izoh + amal tabletkasi; satrlar orasida ingichka ajratgich.
- Asosiy tugma: iliq tilla gradient, qorong‘i matn; ikkinchisi shaffof va tilla konturli.
- Menyu: to‘liq kenglikdagi iliq gradient va chap yorqin chiziq.
- Libos kartasi: katta portret surat, burchakda reyting, pastda nom/ijara/miqdor. Surat asosiy vizual og‘irlikni oladi.

7. **Sizning shablondagi eng muhim besh farq**

1. Main **1440×1383**, GPT dashboard **1672×941**: sizda ko‘proq vertikal yurish talab qilinadi.
2. Sizda ketma-ket **3 → 2 → 3 → 2** blok; GPT’da **4 → 3 → 4**, o‘rtasi turli enli.
3. Sizning foningiz CSS’da **330px** ichida so‘nadi; GPT’da foto KPI bilan kuchliroq tutashadi.
4. Sizning `.panel` konturi `.14`, GPT ko‘rinishida qirralar, ichki yorug‘lik va sirt gradienti kuchliroq.
5. Sizda liboslar kichik ro‘yxat eskizlari, raqamlar ko‘pincha Forum serifida; GPT’da katta galereya va qalin sans-serif raqamlar ustun.

8. **Murosa**

Shisha sirt, yuqoridagi foto, **5/4/3 bento**, katta libos suratlari va aniq faol menyuni saqlang. Fon detalini ma’lumot ortida pasaytiring; kategoriyalarni ranglashni kamaytiring. Tillani asosiy amal va tanlovga, qizilni kechikishga ajrating; yashilni muvaffaqiyat tasdig‘ida ishlating. KassaMinimal’dagi vazifaga qarab guruhlashni saqlab, unga kuchliroq sarlavha va panel chegaralarini qaytaring.

Quyidagi CSS shu tinchroq murosa uchun; `--salon-photo`ga mavjud foto URL’ini bering. Fayllar o‘zgartirilmadi.

```css
:root{
  --bg:#0d1320;--text:#f5f2ee;--muted:#b7bac5;
  --gold:#f3bf70;--gold2:#e8ad5c;--blue:#79a9f2;
  --green:#62d4a3;--red:#f08089;--line:rgba(236,190,120,.30);
  --glass:rgba(18,23,34,.84);--gap:14px;--radius:16px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:400 14px/1.4 "Roboto Condensed",sans-serif}
button,input{font:inherit}
.mazmun{position:relative;isolation:isolate;padding:18px 18px 24px}
.mazmun::before{content:"";position:absolute;z-index:-1;
  inset:0 0 auto;height:520px;pointer-events:none;
  background:linear-gradient(180deg,rgba(13,19,32,.25),
  rgba(13,19,32,.65) 55%,var(--bg)),
  radial-gradient(ellipse at 60% 8%,transparent,rgba(0,0,0,.5)),
  var(--salon-photo,none) center top/cover no-repeat}
.panel,.kpi{border:1px solid var(--line);border-radius:var(--radius);
  background:linear-gradient(145deg,rgba(255,255,255,.06),transparent 65%),
  var(--glass);backdrop-filter:blur(16px) saturate(115%);
  box-shadow:inset 0 1px rgba(255,255,255,.10),0 12px 28px #0004}
.panel{padding:16px}
h1{margin:0;font:500 42px/1.05 "Cormorant Garamond",serif}
.panel-bosh{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.panel-bosh h2{margin:0;font-size:18px;font-weight:600}
.panel-bosh .son,.panel-bosh .havola{margin-left:auto}
.dashboard-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));
  gap:var(--gap);align-items:stretch}
.dashboard-grid>.kpi,.dashboard-grid>.bottom{grid-column:span 3}
.dashboard-grid>.chart{grid-column:span 5}
.dashboard-grid>.gallery{grid-column:span 4}
.dashboard-grid>.list{grid-column:span 3}
.kpi{--accent:var(--gold);position:relative;overflow:hidden;
  display:flex;align-items:center;gap:14px;min-height:100px;padding:12px}
.kpi .belgi{width:56px;height:56px;flex:none;border-radius:22px;
  display:grid;place-items:center;color:var(--accent);
  background:color-mix(in srgb,var(--accent) 20%,transparent)}
.kpi b{display:block;font-size:26px;line-height:1.15;font-weight:700}
small,.mute{color:var(--muted);font-size:12px}
.trend-pill{position:absolute;right:12px;top:12px;padding:2px 7px;
  border-radius:99px;background:#62d4a326;color:var(--green);font-size:11px}
.kpi .sparkline{position:absolute;right:0;bottom:0;width:44%;height:38px;
  color:var(--accent);pointer-events:none}
.sparkline .area{fill:url(#spark-fill)}
.sparkline .line{fill:none;stroke:currentColor;stroke-width:1.5}
.qator{display:flex;align-items:center;gap:12px;min-height:58px;
  padding:8px 0;border-bottom:1px solid #ffffff14}
.avatar{width:42px;height:42px;border-radius:50%;object-fit:cover;flex:none}
.ikki{display:flex;flex-direction:column;min-width:0}
.qator .action{margin-left:auto}
.btn,.btn-2{display:inline-flex;align-items:center;justify-content:center;
  gap:8px;min-height:44px;padding:0 20px;border-radius:99px;font-weight:600}
.btn{background:linear-gradient(120deg,var(--gold),var(--gold2));
  color:#171717;border:1px solid #ffd494}
.btn-2{background:#ffffff04;border:1px solid var(--line);color:var(--text)}
.yon{width:207px;flex:none;background:#0c121ee8;border-right:1px solid #ffffff18}
.nav.faol{background:linear-gradient(90deg,#f3bf7038,#ffffff08);
  box-shadow:inset 4px 0 var(--gold);border-radius:10px;color:var(--text)}
.libos-card{position:relative;min-width:0}
.libos-card img{display:block;width:100%;aspect-ratio:4/5;object-fit:cover;
  border-radius:12px;margin-bottom:8px}
:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
@media(max-width:1000px){.dashboard-grid>*{grid-column:span 6!important}}
@media(max-width:700px){.dashboard-grid>*{grid-column:1/-1!important}}
```

SVG’dagi `spark-fill` gradienti tepadan `.35` opacity bilan boshlanib, pastda `0` bo‘lsin; bir nechta sparkline uchun ID’larni noyob qiling.