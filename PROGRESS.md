# PROGRESS — Libosa

Kelin liboslari salonlari uchun ko'p salonli ijara platformasi. TZ: `TZ_Kelin_liboslari_saloni_v1.2.docx` (Desktop).
Holat (2026-10-13): 44 qism bajarilgan. A'zo bo'lish formasi xatosi tuzatildi (migratsiya `0022` yetishmayotgan edi) va backend qayta yoqildi — tafsilot pastdagi oxirgi yozuvda.
2026-10-13: **A'zo bo'lish formasi tuzatildi, backend qayta yoqildi** — foydalanuvchi xabari «azo bo'lish formasi ishlamay qoldi, yuborib bo'lmadi keyinroq urinib ko'rin degan yozuv chiqdi», keyin «backend ishlamay qolgan ekan». **Sabab:** oldingi ishda `PlatformaSozlama` ga uchta maydon qo'shilgan (`telegram_chat_id`, `telegram_ulash_kod`, `telegram_ulash_tugaydi`), lekin migratsiya yaratilib qo'llanmagan edi. Forma saqlangach `platforma_arizasi()` → `platforma_sozlama()` → `get_or_create(id=1)` to'liq SELECT qilardi va «column does not exist» bilan yiqilardi; chaqiruv `transaction.on_commit` ichida bo'lgani uchun istisno yuqoriga chiqib 500 («yuborib bo'lmadi») qaytarardi. **Tuzatish:** (1) `makemigrations tenants` + `migrate` — `0022` migratsiyasi yaratildi va qo'llandi (`showmigrations tenants` barchasi `[X]`); (2) `platforma_arizasi()` tanasi to'liq `try/except` ga olindi — endi xabarnomadagi har qanday xato so'rovni hech qachon buzmaydi («xabarnoma so'rovni hech qachon buzmasin» qoidasi). **Backend:** RAM kamligidan (7,9 GB dan ~385 MB bo'sh) o'zi o'chgan edi — `runserver --noreload` bilan qayta yoqildi. **Tekshirildi:** `POST /api/auth/ariza/` endi `{"qabul":true}` (201) qaytaryapti, sinov yozuvi tozalandi.
2026-10-13: **Rahbar dashbordi UI/UX jilolandi — 8 ta kamchilik topilib tuzatildi** — foydalanuvchi so'rovi «dashboard ui ux internetdan qidir; top, to'g'rila, kamchilikka tekshir, xolis baho ber, mukammal bo'lishiga nima yetmayapti tahlil qil, tuzat, mukammal bo'lguncha davom et». WebSearch/WebFetch fcc-claude proxida bloklangan (400), shu sabab professional dashbord dizayn bilimidan foydalanildi. Xolis baho natijasi — 8 ta kamchilik, barchasi yopildi: (1) o'tgan davrga nisbatan o'sish/pasayish yo'q edi → `.trend` qatori (`pnl.taqqos.otgan_oy` + `ozgarish`, faqat `davr === 'oy'` da, tushum va sof foyda uchun ▲/▼/·); (2) KPI kartalarda belgi yo'q edi → `BELGILAR`/`Ikona` inline SVG (lucide uslubida, yangi dependency yo'q); (3) asosiy metrika ajratilmagan edi → «Bugun tushum» ga `.kpi-asosiy` (to'yingan oltin fon + kattaroq qiymat); (4) «Yuklanmoqda…» yalang'och matn edi → shimmer skeletonga almashtirildi (`.dashbord-skelet` + `@keyframes skelet`); (5) `.diqqat-blok` CSS sinfi o'lik edi → qizil chap chiziq + qizil tus qoidasi qo'shildi (JSX da allaqachon qo'llangan); (6) klaviatura fokusi ko'rinmasdi → `:focus-visible` tilla halqa (button/a/select/input/textarea); (7) «hammasi joyida» bo'sh holat yo'q edi → `.barchasi-joyida` yashil belgi + Bildirishnomalar ternariga `else` shox; (8) ijobiy/yashil rang yo'q edi → `--yaxshi: #7ecb8f` + `.kpi-delta.yaxshi`/`.past`. `npm run build` o'tdi (Vite 8.3.4, 117 modul, 486 ms). **Birinchi ish: ekranda ko'rish** — KPI kartalar belgilar va trend bilan, asosiy tushum kartasi ajralib turishi, yuklanishda shimmer, bo'sh holatda «✓ Barchasi joyida», qizil Diqqat bloki, klaviatura fokus halqasi.
2026-10-13: **Rahbar dashbordi professional tartibga keltirildi, ortiqcha chap panelga ko'chirildi** — foydalanuvchi so'rovi «dashbordni professional ko'rinishga olib kel; ortiqchani chap panelga ko'chir, hammasini o'rtaga tiqib tashlama». Markazdagi ortiqcha ikkilamchi bloklar (Bugun tafsiloti, Oldinda, Diqqat talab) chap `nav.pastki` panelga ixcham xulosa qilib ko'chirildi: yangi `components/DashbordYon.jsx` (`dashbord('oy')` + `qarzdorlar()` ni 60 s da yangilab, faqat keng ekranda `display:flex`, tor ekranda `display:none`) — Tushum/Smena/Olib-qaytar, Bandlik, Qarzdorlar (6 tagacha + «yana N ta»), Qoldiq kutilmoqda, Qoplamagan qatorlari tugma ko'rinishida tegishli bo'limga o'tadi. `Dashbord.jsx` da tepada yangi `.dashbord-bosh` toolbar (sarlavha + sana + DAVR segment + filial select bir qatorda), 6 ta `.kpi` karta tilla yuqori chiziq + hover ko'tarilishi bilan; ikkinchi darajali bloklar `.dashbord-yon-mobil` ga o'raldi (faqat mobil), takroriy «Davr» jadvali olib tashlandi (raqamlari KPI + P&L da bor). `App.jsx` da `{rahbar && sahifa === 'dashbord' && <DashbordYon onBolim={setSahifa} />}` `nav.pastki` ichiga ulandi. `index.css` da `.dashbord-bosh`/`.dashbord-sarlavha`/`.kpi` aksenti/`.dashbord-yon` qoidalari qo'shildi. `npm run build` o'tdi (Vite 8.3.4). **Birinchi ish: ekranda ko'rish** — desktop (≥768px) da markaz faqat KPI + Bildirishnomalar + grafik + P&L, chap panelda ixcham xulosa; mobil (<768px) da xulosa markazda qoladi.
2026-10-13: **Dashbord vidjetlari birlashtirildi, filtr qo'shildi, «Boshlash» chap panelga ko'chirildi, amortizatsiya olib tashlandi** — foydalanuvchi so'rovi «dashborddagi vidjetlarni imkoni borini birlashtir filtr qo'y; boshlash qismini chap panelga o'tkazib yubor; amartizatsiyani olib tashla har yerdan». (1) `Dashbord.jsx` da «Boshlash» bo'limi butunlay olib tashlandi (endi chap paneldan ko'rinadi); «Tasdiq kutmoqda» + «Ogohlantirishlar» bitta **«Bildirishnomalar»** blokiga birlashtirildi (segment filtr: Hammasi / Tasdiq / Og'ohlantirish — `bild` state); «Qarzdorlar» + «Qoplamagan va bo'sh liboslar» bitta **«Diqqat talab»** blokiga birlashtirildi. (2) «Boshlash» ro'yxati `App.jsx` dagi `nav.pastki` chap panelga ko'chirildi (`bosh` state, faqat rahbar ko'radi; har qadam o'z bo'limiga o'tadi; «Ro'yxatni yashirish» `boshlashYop` bilan) — `index.css` da `.boshlash-panel` tor ekranda `display:none`, ≥768px da ko'rinadi. (3) Amortizatsiya hamma joydan olib tashlandi (backend model/migratsiya/PNL, frontend, testlar) — `makemigrations --check` «No changes detected», grep `amortiz` toza, 611 test o'tdi. `npm run build` o'tdi (Vite 8.3.4). **Birinchi ish: ekranda ko'rish** — dashbordda birlashtirilgan bloklar va filtr, chap paneldagi «Boshlash», amortizatsiya hech qayerda ko'rinmasligi.
2026-10-13: **Rahbar dashbordi professional ko'rinishga keltirildi** — foydalanuvchi so'rovi «rahbar dashbordini professional ko'rinishga keltir». Avval `Dashbord.jsx` bitta 480px li `div.stack` ustunida `.blok` bo'limlarini ketma-ket ko'rsatardi (Bugun jadvali, davr switcher, Oldinda, P&L) — KPI metrika kartalari va vizual iyerarxiya yo'q edi. Endi: (1) tepada 6 ta KPI karta (`kpi-tor` grid) — bugungi tushum, davr daromadi, sof foyda (salbiy bo'lsa qizil), bandlik, kutilayotgan daromad, zakazlar soni; (2) `.dashbord-sahifa` sinfi va `.ilova main:has(.dashbord-sahifa) { max-width: 1100px }` orqali keng ekranda kengaytirildi; (3) Tasdiq/Ogohlantirishlar bloklari yuqoriga (harakat talab qiluvchi bo'lim sifatida) ko'chirildi, Bugun/davr/Oldinda bloklari `.dashbord-ustunlar` 3 ustunli grid'ga o'raldi; (4) bo'lim sarlavhalariga tilla aksent (`border-left: 3px solid var(--tilla)`) va `.tasdiq` kartalariga alohida chekka/fon berildi. Ma'lumot olish va o'zaro ta'sir mantig'i o'zgarishsiz qoldi. `npm run build` o'tdi (Vite 8.3.4). **Birinchi ish: ekranda ko'rish** — rahbar dashbordida KPI kartalar tepada, desktop (≥768px) da uch ustunli stat bloklari, mobil (<768px) da ustunma-ustun.
2026-10-13: **Obuna tugash muddatini o'zgartirish egiluvchan qilindi** — foydalanuvchi so'rovi «obuna tugash muddatini o'zgartirishni gipkiyroq qil». Avval platforma paneli obunani faqat «To'lov: 1/3/12 oy» tugmalari bilan uzaytirar, `Salon` PATCH esa faqat `sinov_tugaydi` ni qabul qilar edi (`obuna_tugaydi` to'g'ridan-to'g'ri belgilanmasdi). Endi: backend `views_platforma.py` da `PlatformaSalonView.patch` serializer'iga `obuna_tugaydi` qo'shildi (ikkala sana ham `allow_null=True` — tozalash mumkin), `patch` da `obuna_tugaydi` ham qo'llanadi; frontend `Platforma.jsx` da har salon blokiga `ObunaSana` komponenti qo'shildi — «Sinov tugaydi» va «Obuna tugaydi» sanalari uchun ikkita `type="date"` maydon + «Sanalarni saqlash» tugmasi (bo'sh → null). `key` prop refetch'dan keyin maydonlarni server holatiga sinxronlash uchun. `obunani_yangila()` patch oxirida `holat`ni sanalardan qayta hisoblaydi. Mavjud «To'lov: 1/3/12 oy» tugmalari tez amal sifatida saqlanib qoldi. `npm run build` o'tdi (Vite 8.3.4); `apps.tenants.test_platforma` 27 test o'tdi. **Birinchi ish: ekranda ko'rish** — platforma panelida salonni ochib ikki sana maydonini to'ldirish, saqlash, «faqat ko'rish» holatiga o'tishi.
2026-10-13: **Platforma paneliga chap tarafdagi nav qo'shildi** — foydalanuvchi so'rovi «chaptarafdagi panelni platformada ham qil». Avval `Platforma.jsx` barcha bo'limlarni (Telegram, salon forma, arizalar, tariflar, salon ro'yxati) bitta uzun `div.stack` da ko'rsatardi. Endi rahbar tomonidagi `nav.pastki` uslubi bilan bir xil: `BOLIMLAR` (Salonlar / Tariflar / So'rovlar / Telegram bot) qo'shildi, `bolim` state'iga qarab nav tugmalari faol belgilanadi va `Panel` faqat tanlangan bo'limni render qiladi («Chiqish» tugmasi va xabar har bo'limda ko'rinadi). `Panel({ bolim, onChiqish })` imzosi yangilandi, bo'limlar `{bolim === '...' && ...}` shartlari bilan ajratildi. `npm run build` o'tdi (Vite 8.3.4). **Birinchi ish: ekranda ko'rish** — platforma (`#platforma`) ga kirganda chap nav, bo'lim tugmalari almashishi va har bo'limda faqat o'z mazmuni chiqishi.
2026-10-12: **Bitta Libosa boti butun platformaga xizmat qiladi (FT-4.14)** — foydalanuvchi qarori: «hamma salon uchun bitta bot hizmat qilsachi, libosa boti platforma egasi kiritadi». Ilgari har salon o'z bot tokenini kiritardi; 100 ta salon = 100 ta token degani edi — har biri alohida `getUpdates` long poll yuritishi, BotFather'da akkauntga ~20 ta bot chegarasi va bitta jarayonning ketma-ket aylanishi muammo bo'lardi. Endi **yagona platforma boti**: token yangi singleton `PlatformaSozlama` da (migratsiya `0021`), bo'lmasa `.env` (`settings.TELEGRAM_BOT_TOKEN`) zaxira; nom ham xuddi shunday (`telegram_bot_nomi` → `TELEGRAM_BOT_NAME`). Token **faqat platforma egasi** panelidan kiritiladi (`Platforma.jsx` da «Telegram» bo'limi, `papi.patch('/sozlamalar/')`); saqlashdan oldin `telegram.tekshir` (`getMe`) bilan tekshiriladi — yaroqsiz token saqlanmaydi (400, butun platforma botsiz qolib ketmasligi uchun). Token hech qachon API javobida yoki `Jurnal` da qaytarilmaydi (`password` maydoni). Salon panelida (`Integratsiyalar.jsx`) Telegram endi faqat **ko'rsatiladi** — «platforma hisobi orqali ulangan»; tokenni salon PATCH'i bilan yuborish jimgina tashlanadi (DRF noma'lum maydonni tashlaydi), ya'ni salon o'zini boshqa botga ulay olmaydi. **Bitta botning oqibatlari yopildi:** (1) `telegram.api()` endi tokenni o'zi oladi (`token_ol()`) — chaqiruvchilar token uzatmaydi, `telegram_bot` buyrug'i va `telegram.tekshir(token)` dan tashqari; (2) 429 (`TelegramLimitXatosi`) da xabar **navbatda qoladi** va navbat navbatdagi aylanishga to'xtatiladi — ilgari `XATO` deb belgilanardi va xabar butunlay yo'qolar edi (kunlik hisobot 21:00 da hamma salonga birdan ketadi, limit umumiy); ketma-ket yuborishlar orasiga `YUBORISH_PAUZASI = 0.05` qo'yildi; (3) `start_ishla` bir akkaunt shu **salonning** ikkinchi xodimida qolmasligini ta'minlaydi, lekin **boshqa salonlardagi** bog'lanishni uzmaydi — bitta chat bir nechta salonning xodimi bo'lishi mumkin; (4) chegirma tugmasi (`tugma_ishla`) salonni akkauntdan emas, **so'rovning o'zidan** oladi («faqat shu salon rahbariga ruxsat etilgan») — aks holda boshqa salon rahbari begona so'rovni tasdiqlab yuborishi mumkin edi (ochiq xavfsizlik teshigi edi). `arxiv.salon_modellari()` faqat `Salon` FK li modellarni olgani uchun salon o'chirilganda `PlatformaSozlama` o'chib ketmaydi (tekshirildi). **TZ 7.1 dan ongli chetlanish:** TZ aiogram tavsiya qiladi, lekin bitta bot uchun oddiy `getUpdates` (25 s long poll) yetarli — qo'shimcha kutubxonasiz, mavjud `telegram_bot` buyrug'i asosida qoldirildi. Testlar: `apps.notify` 38 (429 yo'li va salonsiz bog'lanish saqlanishi uchun 2 tasi yangi), `apps.tenants` da FT-4.14 uchun 1 tasi yangi (ikkinchi salon ham o'sha token bilan ishlashi). **Eslatma: migratsiya `0021` — dev bazada `migrate` qilinishi shart.**
2026-10-12: **Kassa bo'limlari ham chap nav panelga chiqarildi** — foydalanuvchi so'rovi «kassani ham». Kassa amallari (Hisobot, Xarajat kiritish, Inkassatsiya, Zaloglarni tekshirish, Smenadan chiqish, Smenani yopish) endi Sozlamalar/Katalog/Mijozlar singari chap `nav.pastki` panelda tugma ko'rinishida; «Smenalar tarixi» faqat rahbarga. Kassa smena holatiga bog'liq bo'lgani uchun smena ochiqligi (`kassaOchiq`) App darajasiga ko'tarildi — `App.jsx` da `kassaBolim`/`kassaOchiq` state'lari va `kassaYukla` useCallback; nav kassa uchun to'rtinchi shartli holat qo'shildi. `Kassa.jsx` `bolim` va `onHolatOzgardi` prop'larini oladi, `yukla` smena holatini o'zgartirganda `onHolatOzgardi` chaqiradi; render `bolim` bo'yicha shartli — smena yopiq bo'lsa «Smena ochish» (yoki rahbar uchun Tarix), ochiq bo'lsa tanlangan bo'lim formasi. `npm run build` o'tdi (Vite 8.3.4). **Birinchi ish: ekranda ko'rish** — smena ochiq/yopiq holatiga qarab nav tugmalari almashishi, har bir bo'lim tugmasi bosilganda mos forma chiqishi, rahbarda «Tarix» tugmasi ko'rinishi.
2026-10-12: **Katalog va mijozlar ichki bo'limlari chap nav panelga chiqarildi** — foydalanuvchi so'rovi «sozlamaniki kabi boshqa bo'limlardagini ham chap tarafga knopka ko'rinishida chiqadigan qil». Ichki tablar faqat `Katalog` (Liboslar/Aksessuarlar) va `Mijozlar` (Mijozlar/Salonchilar/Promokodlar) da bor edi; ular endi Sozlamalar singari chap `nav.pastki` panelda tugma ko'rinishida ko'rsatiladi. `Katalog.jsx`/`Mijozlar.jsx` dan `.segment` ichki tab tugmalari olib tashlandi — `bolim` endi prop orqali keladi (Mijozlar `promoYoq` ni ham prop qilib oldi). `App.jsx` da `katalogBolim`/`mijozlarBolim` state'lari qo'shildi, `sozlamaOldin` umumiy `oldin` ga almashtirildi, `promoYoq` endi `sozlamalar()` dan App darajasida olinadi; nav uch holatga (sozlamalar/katalog/mijozlar) kengaytirildi — har birida «← Orqaga» + tegishli bo'lim tugmalari, «Promokodlar» faqat rahbarga va sozlama yoqilganida. `npm run build` o'tdi (Vite 8.3.4). **Birinchi ish: ekranda ko'rish** — Katalog va Mijozlar bo'limlariga kirganda chap paneldagi tugmalar, «← Orqaga» ishlashi, Promokodlar tugmasi faqat rahbarda ko'rinishi.
2026-10-12: **«Sozlamalarni saqlash» tugmasi panel pastiga ko'chirildi** — foydalanuvchi so'rovi «sozlamani saqlash knopkasi panel tepasida emas pastki tarafida bo'lsin». `Sozlamalar.jsx` da `.sozlama-saqlash` bloki `{joriy.render()}` dan oldin (tepada) emas, keyin (pastda) chiqadi; `index.css` da `position: sticky; top: 0` → `bottom: 0` qilindi (tugma endi panel pastida yopishib turadi). `npm run build` o'tdi.
2026-10-12: **Sozlama bo'limlari asosiy chap panelga, panel foni umumiy fonga** — foydalanuvchi so'rovi «chap tarafdagi qora fondagi panelni fonini umumiy fonga aylantir; paneldan sozlama tanlansa o'sha chap tarafdagi panelga sozlamalarni bo'limlari chiqsin; tepada qaytish knopka bo'lsin; qaytishga bossa yana profil egasi uchun chaptarafda umumiy bo'limlar tugma ko'rinishda chiqadigan bo'lsin». Avvalgi ikki ustunli sozlama layouti (ichki `aside.sozlama-panel`) olib tashlandi — bo'limlar endi AYNAN asosiy `nav.pastki` sidebar'ning o'zida ko'rsatiladi. `Sozlamalar.jsx` dan `SOZLAMA_BOLIMLAR` statik exporti (19 bo'lim) qo'shildi va `bolim` prop orqali tanlangan bo'lim qabul qilinadi; `App.jsx` da `sozlamaBolim`/`sozlamaOldin` state'lari — «Sozlama» tanlanganda `nav` shartli ravishda «← Orqaga» tugmasi + bo'limlar ro'yxatiga almashadi (orqaga bossa `sozlamaOldin` sahifaga qaytadi). `rekvizitlar`/`yordam` endi doimiy bo'lim (render ichida «Yuklanmoqda…» holati). `.pastki` fonini `rgba(14,26,43,.78)` + blur o'rniga `transparent` (qasr foni ortidan ko'rinadi); tugmalarga o'qilishi uchun yengil `rgba(253,250,245,.08)` fon + oq border berildi. `.sozlama-sahifa`/`.sozlama-panel` CSS qoidalari o'chirildi, `main:has(.sozlama-mazmun) { max-width: 1080px }`. `npm run build` o'tdi (Vite 8.3.4). **Birinchi ish: ekranda ko'rish** — desktop (≥768px) da sozlama bo'limlari chap panelda, «← Orqaga» ishlashi, panel fonining shaffofligi; mobil (<768px) da bo'limlar pastdagi navda gorizontal scroll bo'lishi.
2026-10-12: **Sozlamalar sahifasi ChatGPT uslubiga o'tkazildi** — foydalanuvchi so'rovi «sozalamadagi bo'limlar chap panelga ochilsin, o'rtada aynan tanlangan bo'lim». Avvalgi bitta uzun scroll `div.stack` o'rniga ikki ustunli layout: chap `aside.sozlama-panel` da bo'limlar ro'yxati (tugmalar), markaz `div.sozlama-mazmun` da tanlangan bo'lim mazmuni. `Sozlamalar.jsx` qayta yozildi (`tanlangan` holati, `bolimlar` array, har bo'lim `{ id, nomi, render }`), «Sozlamalarni saqlash» tugmasi va `xabar` sticky `.sozlama-saqlash` konteyneriga ko'chirildi (hamma bo'limlar birdan saqlanadi). `index.css` ga `.sozlama-sahifa`/`.sozlama-panel`/`.sozlama-mazmun`/`.sozlama-saqlash` sinflari va `.ilova main:has(.sozlama-sahifa) { max-width: 1080px; }` qo'shildi. Mobil ekranda panel gorizontal scroll tugmalar qatori, keng ekranda (≥768px) chap vertikal sticky panel. `npm run build` o'tdi.
2026-10-11: **Kirish sahifasi fon xatosi tuzatildi** — `#kirish` ekranida fon yo'q edi (ochiq `--fon` fonda oq matn/input ko'rinmasdi). `App.jsx` da `PlatformaFon` Kirish ekraniga ham qo'shildi (kirgan ilova bilan bir xil to'q qasr foni). Build o'tdi.
2026-10-11: platforma brend nomi **Weddy → Libosa** almashtirildi — foydalanuvchi ko'radigan matnlar (UI, SMS/Telegram, arxiv yuklab olish fayl nomi). Texnik identifikatorlarga tegilmadi: `weddy.*` localStorage kalitlari, `weddy-onlayn/oflayn` eventlari, `weddy.device/staff/platform` auth tuzlari, DB paroli (`postgres://weddy:...`), `weddy_bot` test fixturelari. Tarixiy hujjatlar (`docs/*`, `PROGRESS.md` o'tgan yozuvlari) ham o'zgarishsiz.
2026-10-11: **ezaz demo salonida qurilma avto-tasdiq** — foydalanuvchining «ezaz salonini o'zi ga faqat ruxsat» so'rovi. `Salon.qurilma_avto_tasdiq` bayrog'i qo'shildi (migratsiya `0020`), `SalonLoginView` da yoqilgan bo'lsa har bir qurilma darhol ishonchli bo'ladi (FT-22.2 ni chetlab o'tadi — faqat demo_ezaz kabi sinov salonlarida yoqiladi). `demo_ezaz` buyrug'i bayroqni yoqadi. Ishlab chiqarish salonlarida FT-22.2 qoidasi avvalgidek.
2026-10-11: **Kirish sahifasi tugmalari** — foydalanuvchi so'rovi «bosh sahifa knopkasini chap yuqoriga qo'y platforma egasini olib tashla». `App.jsx` da «← Bosh sahifa» tugmasi `position: fixed; top: 12px; left: 12px` (`.kirish-orqaga` sinfi, qasr fon ustida) chap-yuqoriga ko'chirildi; «Platforma egasi» tugmasi olib tashlandi (platforma paneliga kirish reklama sahifasi futeridagi havola va `#platforma` orqali qolmoqda). `npm run build` o'tdi.
**Kod commit qilinmagan** (faqat `git add -A`; 44-qism fayllari hatto `git add` ham qilinmagan). **Davom ettiruvchi agent: avval pastdagi «44-qism» bo'limini o'qi.**
Har qismning to'liq tarixi (nima, nega, qanday sinalgan): `docs/PROGRESS_ARXIV.md` — faqat kerak bo'lganda o'qi.

## Ishga tushirish
```bash
docker compose up -d db                      # PostgreSQL 16, port 5433 (5432 band)
cd backend && .venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py runserver     # API :8000
.venv/Scripts/python manage.py test          # 603 ta test, ~10 daqiqa; ikki test jarayonini birga ishlatma
cd ../frontend && npm run dev                # :5173;  npm run lint / build
```
- Demo: `manage.py demo_ezaz` (salon `ezaz`; parol va PIN lar shu buyruq faylida). Platforma egasi: `manage.py platforma_admin <login>`.
- Telefondan (shu Wi-Fi): backend `DEV_LAN=1 ... runserver 0.0.0.0:8000`, frontend `npm run dev:lan`. Faqat `DEBUG` da, faqat xususiy tarmoq.
- Yangi migratsiyadan keyin dev bazada `migrate` — unutilsa 500.

## Arxitektura
- **Backend** `backend/apps/`: Django 5.2 + DRF, psycopg3. Har jadvalda `salon` (abstract `SalonModel`); har so'rov `request.salon` bo'yicha.
  Biznes mantiq servis fayllarida, xato sinflari (`...Xatosi`) view da 409 ga aylanadi.
- **Auth**: salon logini → qurilma tokeni (`X-Device-Token`) → xodim PIN → Bearer token. Platforma egasi — alohida token.
  Yangi qurilma rahbar ruxsatini kutadi. Rahbar Telegram ulagan bo'lsa PIN + kod.
- **Frontend** `frontend/src/`: React + Vite, JSX, oddiy CSS (`index.css`), router yo'q (`App.jsx` da holat), barcha so'rovlar `api/index.js` orqali.
- Til: kod izohlari, UI va commit xabarlari o'zbekcha.

| Ilova | Nima bor | Asosiy fayllar |
|---|---|---|
| `tenants` | salon, xodim, qurilma, obuna/tarif, platforma paneli, sozlamalar (`SalonSozlamalari`), integratsiyalar, filiallar, jurnal, salon arxivi/o'chirish | `models`, `auth`, `views_admin`, `views_platforma`, `views_integratsiya`, `views_filial`, `arxiv` |
| `catalog` | kategoriya, libos, rasm (WebP), aksessuar va donalar, ta'mir jurnallari, manekin (fonsiz qatlam) | `services`, `rasm`, `tamir`, `dona_tamir`, `manekin` |
| `bookings` | bron (`ExclusionConstraint`), qulf, aksessuar broni, bo'sh liboslar, kalendar | `services`, `views` |
| `orders` | mijoz, salonchi, zakaz, zalog, berish/qaytarish, chegirma, promokod, mavsumiy narx, primerka, o'zgartirish/bekor, hujjatlar, to'lov havolasi, bosh ekran, dashbord | `services`, `rental`, `discounts`, `promo`, `pricing`, `primerka`, `changes`, `hujjatlar`, `tolov_havola`, `views_royxat` |
| `cash` | smena (umumiy yoki filial bo'yicha), to'lovlar, kassa hisoboti, zalog tekshiruvi, smenani tuzatish | `services`, `tekshiruv` |
| `finance` | xarajat, moddalar, doimiy xarajatlar, P&L (+filial, tafsilot), 16 hisobot, bonus, bank solishtiruvi, oyni yopish | `services`, `moddalar`, `reports`, `statistika` |
| `notify` | Telegram (xabar navbati, ulash, kirish kodi), SMS (Eskiz) | `telegram`, `services`, `sms` |

Frontend sahifalari: Reklama (bosh sahifa: `pages/Reklama.jsx` + `reklama.css`, WebGL foni va zarracha shakllari `pages/reklamaSahna.js` da;
43-qismda qo'shilgan bloklar — `QasrVideo.jsx`+`gulbargSahna.js`+`reklama-qasr.css`, `Kelinlar.jsx`+`gologramma.js`+`kelinlar.css`;
44-qismda — `Tashvishlar.jsx`+`tashvishlar.css` («Imkoniyatlar» slayderi), `Yakun.jsx`+`yakun.css` (yakuniy qism); `OyinKartalar.jsx`+`kartalar.css` ulanmagan), Kirish, Dashbord, BoshEkran, YangiZakaz, Zakazlar, Mijozlar (+Salonchilar, Promokodlar), Kalendar, Katalog (+AksessuarBolimi),
Kassa, Hisobotlar, Sozlamalar, Platforma, Oflayn. Komponentlar: Manekin, Integratsiyalar, Xarajatlar, MavsumiyNarx, RasmBlok, TamirBlok, Vitrina, Hujjat, OylikGrafik.

Buyruqlar (cron): `bronlarni_tozalash` (15 daq.), `eslatmalarni_yuborish` (soatda), `kunlik_hisobot` (15 daq.; salon o'z vaqtida oladi),
`sms_eslatmalar` (kuniga 1), `telegram_bot` (doimiy jarayon), `chiqqan_salonlar [--arxiv|--ochirish]` (qo'lda).

## Muhim qoidalar (o'zgartirishdan oldin bil)
- **Daromad** = zakaz to'liq to'langan kuni (`Zakaz.tolangan_sana`); kutilayotgan daromad P&L ga kirmaydi. Narx oshib qoldiq chiqsa sana tozalanadi.
- **Narx**: asosiy (libos + aksessuar + moslash xizmati) + mavsumiy ustama − chegirma/promokod. Chegirma ustama qo'shilgan summadan.
- Chegirma va promokod faqat avans olinmagan zakazga; tayyor chegirma tasdiqsiz, boshqasi rahbar tasdig'i bilan.
- «Berildi» dan keyin zakaz o'zgartirilmaydi va bekor qilinmaydi.
- To'lov **xodim ishlayotgan smenaga** yoziladi (`cash.services.xodim_smenasi`); ochiq smenasiz to'lov yo'q.
- Sotuvchi tannarxni ko'rmaydi; sotuvchi xarajati kassadan va rahbar tasdig'i bilan; hisobotlar faqat rahbarga va fayl sifatida yuklanmaydi.
- Xabar/SMS yuborishdagi xato asosiy amalni hech qachon buzmaydi.
- Sanalarni `timezone.localtime(...)`/`localdate()` bilan ol (`.date()` to'g'ridan-to'g'ri UTC beradi — shu xato bo'lgan).

## TZ dan chetlanishlar va o'zim qabul qilgan qarorlar (foydalanuvchi hali tasdiqlamagan)
- Xarajat kiritish 1-bosqichga olingan; PDF o'rniga brauzerning chop etish oynasi; aiogram o'rniga to'g'ridan-to'g'ri Bot API;
  to'liq sozlash ustasi o'rniga «boshlash ro'yxati»; aksessuar uchun 15 daqiqalik qulf yo'q.
- Mavsumiy narx: bir kunga bir nechta qoida — eng katta foiz (qo'shilmaydi). Ustama moslash xizmatiga ham qo'llanadi.
- Sotuvchi bonusi P&L operatsion xarajatiga avtomatik qo'shiladi (qo'lda qayta kiritilmasin).
- Shartnomaning avtomatik bandlari tahrirlanmaydi; salon faqat qo'shimcha band qo'shadi.
- Filial: qurilma orqali aniqlanadi (xodim filialga biriktirilmaydi). Filial kassasi sozlama bilan (`filial_kassasi`, standart: o'chiq).
  Filial P&L ga umumiy (filialsiz) xarajat, libos va zakazlar kirmaydi — filiallar yig'indisi salon natijasiga teng emas.
- Smena tekshirilmagan zalog bilan ham yopiladi (rahbarga xabar boradi).
- Bosh manzil (`/`) kirmagan odamga reklama sahifasini ko'rsatadi; kirish ekrani — `/#kirish`. Xodim chiqsa yoki harakatsizlikdan keyin
  kirish ekraniga qaytadi (reklamaga emas). «A'zo bo'lish» hisob ochmaydi: so'rov (`tenants.Ariza`) platforma egasi paneliga tushadi,
  salonni egasi qo'lda ulaydi. Bitta raqamdan sutkasiga 3 ta, jami 200 ta so'rov.
- Xarajat o'chirilmaydi: rahbar «bekor qilsa» `rad` holatiga o'tadi. Kassadan to'langan xarajat bekor qilinmaydi, summasi/sanasi o'zgarmaydi;
  yopilgan oyda va bank komissiyasi yozuvida tuzatish yo'q. Kategoriya faqat bo'sh bo'lsa o'chadi; tayyor chegirma va tarif o'chmaydi — nofaol qilinadi
  (salon ulangan tarif yopilmaydi).
- Salon arxivi faqat «chiqqan» salonga beriladi; o'chirish faqat buyruq bilan, avtomatik emas.
- Integratsiyalar salon darajasida (`.env` — zaxira). Click/Payme: faqat to'lov havolasi, maxfiy kalit saqlanmaydi, webhook yo'q.
- Bot tokeni va Eskiz paroli bazada ochiq matnda (API, jurnal va arxivga chiqmaydi).

## Tekshirilmagan / ma'lum xavflar
- **43-qism (reklama sahifasi, lusion.co/about uslubida qayta ishlash)** — brauzerda (1400×850) ko'rilgan, foydalanuvchi bilan birga sozlangan.
  Sahnalar tartibi (44-qismdan keyin): bosh kadr (qasr videosi) → Kelinlar gologrammasi → «Imkoniyatlar» slayderi → yakuniy qism → a'zo bo'lish formasi → oyoq.
  Tafsilot: `docs/PROGRESS_ARXIV.md` → «43-qism». **Sinalmagan:** telefon/tik ekran (390×844), `prefers-reduced-motion`, WebGL'siz holat,
  `npm run build` va `npm run lint` (Linux VM da rolldown'ning Windows binary'si ishlamadi — Windows'da o'zing ishga tushir).
  Ma'lum kamchiliklar: `qasr.mp4` all-intra emas (kalit kadr faqat boshida) — aylantirishda sakrashi mumkin, `-g 1` bilan qayta kodlash kerak;
  `Reklama.jsx` dagi `BoshVideo` funksiyasi ishlatilmaydi (lint ogohlantiradi); kelin rasmlari (`public/kelinlar/1–5.jpg`) 2×2 kollajdan kesilgan.
- **44-qism (2026-10-11): reklama sahifasining o'rta va pastki qismi qayta qurildi.** Foydalanuvchi bilan birga, brauzerda ko'rib sozlangan.
  Lint va build o'tgan (`Tashvishlar.jsx` da 2 ta ortiqcha-ehtiyotkor lint ogohlantirishi bor — xato emas).

  **A) «Imkoniyatlar» slayderi** — `pages/Tashvishlar.jsx` + `tashvishlar.css`, fayllar `public/tashvish/`. Orano «Innovation» uslubi.
  - Avvalgi «Uch tashvish» va «Imkoniyatlar» o'yin kartalarini birlashtiradi; `id="imkoniyatlar"` (menyu shu yerga olib keladi).
  - 8 slayd: Bron, Zakaz, Katalog, Kassa, Foyda, Mijozlar, Eslatmalar, Filiallar. Har birida shior + 4 imkoniyat (`SLAYDLAR` massivi), takror yo'q.
  - Har slaydga `fon-N.jpg` (tilla sim-karkas chizma) va `kelin-N.mp4/.jpg` (milliy libosdagi tilla kelin, aylanma video, har kadr kalit kadr, 800×800).
  - Kelinning o'rni har slaydga alohida: `SLAYDLAR` da `x`, `y` (oyog'i turadigan nuqta, %) va `h` (bo'yi, vh) — fondagi polga moslangan.
  - O'tish — «skaner»: tik tilla nur ekranni kesadi, yangi kadr ortidan ochiladi (CSS clip-path). Yassilanish/RGB/zarracha varianti rad etilgan.
  - Kelin **bosish** bilan aylanadi (bir bosish — to'liq aylanish, bosib surish — qo'lda); kursor faqat fonni siljitadi.
  - Slayd **aylantirishga** bog'langan (`.rk-tv-yol` baland, `.rk-tv` yopishqoq; `mosla`) va **5 s taymer** (`AVTO`; strelka/nuqta/taymer — `borish`).
  - Faqat joriy va ikki qo'shni slayd fayllari yuklanadi. `public/tashvish/1/` — foydalanuvchining ilhom rasmlari, saytda ishlatilmaydi, **o'chirma**.

  **B) Yakuniy qism** — `pages/Yakun.jsx` + `yakun.css`, fayllar `public/yakun/`. jjettas.com uslubi. Avvalgi «raqamlar», «Qanday ishlaydi»,
  «Navbat sizda» bo'limlari o'rniga uchta yopishqoq sahna; harakat faqat CSS da, `Reklama.jsx` har `[data-sahna]` ga yozadigan `--p` (0..1) orqali.
  **Joriy tartib (2026-10-11 oxirgi holat): Chaqiriq → Raqamlar → Kirish** (quyida tarixiy jihatdan eski Kirish→Raqamlar→Chaqiriq tartibida
  yozilgan — tartib 2026-10-11 «Yakuniy qism tiklandi» ishida qayta o'rnatildi):
  1. **Kirish** — to'liq ekranli video `yakun/kirish.mp4` (asli `public/video/video_2026-10-11_01-12-37.mp4`: yonboshlab saqlangan keng video,
     `transpose=2` bilan burilib 1600×900 ga kattalashtirilgan; CSS `mix-blend-mode: color` bilan tilla/sarg'ish rangga bo'yaladi), ustida «Weddy» yorlig'i (2026-10-11 da «raqamlarda» so'zi olib tashlandi — foydalanuvchi so'rovi).
  2. **Raqamlar** — fon `/fon/qasr.jpg` (Kie nano-banana-2 da generatsiya qilingan **chizilgan qasr**, ertak uslubidagi saroy, 1376×768→JPG),
     tepada 4 ta shaffof **guldasta** (`gullar/1–4.png`, Kie orqali generatsiya qilingan, to'q ko'k fon olib tashlangan) Instagram «hikoyalar»
     (story) qatoridagi avatarlar kabi joylashadi (`.rk-yk-gul-qator` → `.rk-yk-gul`): har guldasta doira (`--gul-d`) ichida, faoli o'z
     raqamining oynasida tilla `conic-gradient` halqa bilan yorishib, biroz ko'tarilib kattalashadi (`--faol`), qolganlari xira; halqa doimo
     aylanib turadi. 4 ta raqam (8 / 16 / 14 / 3) chap pastki burchakda avvalgidek bitta-bitta ko'tarilib yorishadi (jjettas uslubi),
     guldastalar shu raqamlar bilan sinxron almashadi. Yuqorida o'ngda 4 ta mayda tilla chiziqcha faol raqamni ko'rsatadi.
     2026-10-11 da foydalanuvchi «boshla» deganidan keyin raqamlar avval markazda kelin ustida almashardi, so'ng «chap pastki burchakka» ko'chirildi;
     keyin «raqamlar bilan o'rtadagi kelinlar ham o'zgarsa» so'rovi bilan yagona shaffof `tojli-kelin.webp` o'rniga 4 ta katalog fotosi arka ramkada qo'yildi.
     Oxirgi so'rov: «kie orqali kelinlar gullarini generatsiya qilib … o'rtada aylanadigan effekt» — avval kelin generatsiya qilina boshlandi
     (2 ta, bekorga ketdi), so'ng foydalanuvchi **gul** (guldasta) demoqchi ekani aniqlandi va 4 ta guldasta (ivory/blush atirgul, oq pion,
     blush/krem, oq+oltin kalla) Kie nano-banana-2 da generatsiya qilindi. Arka ramkali kelin fotolari ana shu karuselga almashtirildi.
     2026-10-11 (keyingi so'rov): «gullarni almashish effekti va fonini o'zgartir, orqa fon chizilgan qasr; gullar o'zi galagramma (Instagram) kabi
     yuqorida, galagrammadagi kelinlar obrazi kabi» — karusel olib tashlanib guldastalar tepaga Instagram story avatarlari qilib ko'chirildi,
     fon chizilgan qasr (`qasr.jpg`) ga almashtirildi.
     2026-10-11 (keyingi so'rov): «qanday ishlaydi zakaz 4 qadamda degan joyii olib tashla» — «Qadamlar» sahnasi (`id="qanday"`, 4 kartochka)
     butunlay olib tashlandi: `Yakun.jsx` dan `QADAMLAR` va 3-sahna bloki, `yakun.css` dan `.rk-yk-qadam`/`.rk-yk-karta`/`.rk-yk-bosh` uslublari,
     `Reklama.jsx` `MENYU` dan «Qanday ishlaydi» havolasi olib tashlandi (endi `#qanday` yo'q). Rasmlar `yakun/karta-1..4.jpg` hali diskda turibdi.
     2026-10-11 (keyingi so'rov): «weddy raqamlarda slaydining foni imkoniyatlar slaydinikidek chizma va guldastalar esa kelinlar slaydidagi
     kabi gologramma effektli bo'lsin» — «Raqamlar» sahnasi (2-sahna) fon va guldastalari almashtirildi:
     - Fon: chizilgan qasr (`/fon/qasr.jpg`) o'rniga «Imkoniyatlar» slaydlaridagi tilla sim-karkas wireframe chizma (`/tashvish/fon-1.jpg` —
       «Saroy zali»). `yakun.css` da `.rk-yk-fon` dan blur/brightness olib tashlandi, opacity .58 (wireframe uslubida); `::before` qoraytirish
       multiply o'rniga yengil chap/chet gradientiga almashtirilib z-index 1 ga ko'tarildi (chizmani o'chirmay matn o'qilishini ta'minlaydi).
     - Guldastalar: Instagram «story» avatar rasmlari (`gullar/1–4.png`) o'rniga «Kelinlar» slaydidagi nuqtali gologramma (WebGL). Har guldasta
       o'z kichik kanvasida bitta obrazdan yig'iladi; `gologramma.js` ga ixtiyoriy `soni` (nuqtalar soni) parametri qo'shildi — guldastalar
       uchun 1800 (standart 22000, Kelinlar orqaga mos). Faol guldasta CSS bilan yorishib kattalashadi, gologramma o'zi doim «nafas oladi».
       WebGL bo'lmasa guldastalar bo'sh tilla halqa bo'lib qoladi (Kelinlar kabi, alohida fallback yo'q). `gullar/1–4.png` va `/fon/qasr.jpg`
       endi ishlatilmaydi (diskda qoladi, tozalash faqat so'ralsa).
     2026-10-11 (keyingi so'rov): «gullar bitta bitta ramkasiz markazda chiqsin» va «hajmini ham kattaroq qil» — guldastalar bitta markazdagi
     katta kanvasga ko'chirildi:
     - 4 ta alohida kichik kanvas (har biri 1800 nuqta, `.rk-yk-gul` halqa+disk ramkasida) olib tashlandi; o'rniga `Yakun.jsx` da bitta
       markazdagi `<canvas>` (ref `gul`) va bitta `gologrammaYarat(gul, GULLAR)` — standart 22000 nuqta, bitta WebGL konteksti (xotira kam
       bo'lgani uchun afzal).
     - Faol guldasta `tanla(i)` bilan almashadi: `Yakun.jsx` scroll/resize da `--q` bilan bir xil formula (Reklama.jsx yozayotgan `--p` dan)
       bo'yicha indeks hisoblaydi — guldasta raqam bilan sinxron, gologramma eskisini sochib yangisini yig'adi (bitta-bitta almashish).
     - Ramka olib tashlandi: `yakun.css` dan `.rk-yk-gul`, `::before` (aylanuvchi tilla halqa), `::after` (to'q disk) va `@keyframes
       rk-yk-aylan` o'chirildi; guldasta endi `.rk-yk-gul-qator` da ekran markazida (`left/top 50%`), ramkasiz.
     - Hajmi kattalashtirildi: `--gul-d` min(13vh,16vw) dan min(40vh,46vw) ga; telefon media query'da min(32svh,66vw), markazdan biroz tepaga
       (46svh). `gullar/1–4.png` gologrammaning manbasi bo'lib qolmoqda (o'chirilmagan); `/fon/qasr.jpg` endi ishlatilmaydi.
     2026-10-11 (keyingi so'rov): «jjettas.com saytidagi "I want people to remember me for" yozuvining stilini/effektini o'rganib, Weddy'dagi
     "Saloningiz Weddy'ga tayyormi?" yozuviga qo'lla» — Chaqiriq sahnasi harfma-harf yorishishdan so'zma-so'z yorishishga o'tkazildi (jjettas.com
     uslubi: katta serif, har so'z xira+blur holatdan ketma-ket yorishib o'tkirlashadi):
     - `Yakun.jsx`: `SOZLAR` endi harf juftligi emas, balki so'zlar ro'yxati (`SAVOL.split(' ')`); `HARFLAR` o'rniga `SOZ_SONI`. JSX da har so'z
       bitta `<i>` (o'z `--i` indeksi bilan), `<span>` qatlami olib tashlandi; `--harf` o'rniga `--soz`.
     - `yakun.css`: `.rk-yk-chaqiriq h2 i` — opacity .12→.88, translateY .3em, blur 9px (xira+blur'dan o'tkirga o'tish), so'nggi so'z
       («tayyormi?») `:last-child` bilan tilla kursiv ta'kid; `--h` formulasi `var(--soz)+1` — 3 so'z 0→~46% ulushga yoyiladi, tugma 64% da.
     - jjettas.com jonli ko'rilmagan (WebFetch faqat matn berdi, CSS/animatsiya tafsilotlari berilmadi) — stil Lusion uslubi va matn tuzilishidan
       chiqarildi.
  3. **Chaqiriq** — «Saloningiz Weddy'ga tayyormi?» so'zma-so'z yorishadi (jjettas.com uslubi), keyin «A'zo bo'lish» (`onAzo`). `data-t="5"` — fondagi WebGL libos.
  - `Reklama.jsx` dan olib tashlangan: `rk-galereya` bloki, `Kartalar`, `KARTALAR`, `RAQAMLAR`, `LENTA`, `QADAMLAR`, `Sanoq` (CSS'lari `reklama.css` da qolgan).
  - Sayt ikonkasi (`public/favicon.svg`) EZAZ malika belgisiga almashtirilgan (`pages/ezazBelgi.js` dagi vektordan).

  **Tekshirilgan:** A) 8 slaydning hammasi 1920×911 da, skaner o'tishi, 5 s taymer, g'ildirak bilan ikki tomonga aylantirish, bosib/surib aylantirish
  (faqat 8-slaydda). B) uch sahnaning statik holatlari 1920 kenglikda (`--p` qo'lda qo'yib), kirish videosi ijro etilishi.
  **Tekshirilmagan:** B) ning jonli aylantirishdagi silliqligi; ikkala qismning telefon/tik ekrani (CSS yozilgan, lekin ko'rilmagan — A) da tor oynada
  bir marta ko'rilgan, keyin o'zgargan); `prefers-reduced-motion`; A) da 1–7-slaydlarda bosib aylantirish.
  **Ma'lum kamchiliklar:** 8-kelinning (Toshkent) orqa ko'rinishi siyrak; 3-kelinning fatasi aylanganda kadr chetiga tegadi; 1–2-kelin videosida
  boshi va oxiri aynan bir xil emas (surishda kichik sakrash bo'lishi mumkin); `kirish.mp4` manbasi past sifatli — katta ekranda yumshoq;
  jjettas.com jonli ko'rilmagan (tuzilishi DOM dan o'qilgan) — foydalanuvchi aniq harakatni so'rasa, saytni ko'rinadigan oynada ochib qarash kerak.

  **Generatsiya va asl fayllar** (qayta yaratish kerak bo'lsa): `generate` skill, ishchi papka `F:\Cowork\claude image\` (kalit o'sha yerdagi `.env` da —
  chop etma). Asl rasm/videolar `generations/weddy_*`, jurnal `generations/log.jsonl`. Kie AI: ~530 kredit qolgan (rasm ≈12, 5 s video = 70 kredit).
  Artlist: 195 kredit (2026-11-10 da yangilanadi), Higgsfield: 0. 1–2-kelin videolari Artlist'da (Seedance 2.0 Mini), qolgani Kie'da (Kling 3.0).
  Uslub namunalari: `generations/refs/weddy_saroy-tilla.png` (fon), `weddy_kelin-3.png` (tilla kelin), `weddy_tojli-kelin.png` (tojli kelin, yashil fonda).
  Guldastalar (nano-banana-2): asllari `generations/weddy_gul-1..4_*.png` (to'q ko'k fonda), shaffoflanganlari `frontend/public/gullar/1–4.png`;
  `weddy_kelin-1|2-gul_*.png` — xato kelin generatsiyalari (bekorga), ishlatilmadi.
  Fonni kesish: `ffmpeg -i X.png -vf "chromakey=0x0a8433:0.10:0.04,despill=type=green:mix=0.7:expand=0.2,format=rgba" ...` (yashil rangni avval o'lcha).
  `public/video/` dagi ishlatilmaydigan fayllar: `video_2026-10-11_01-12-55.mp4`, `..._01-13-01.mp4` (guldastada «ZANBAGH» yozuvi), `Свадебное платье.mp4`
  («Dola AI» belgisi bor), `bosh_keng|bosh_tor.*`, `libos_bron.*` — foydalanuvchiniki, **so'ramasdan o'chirma**.

  **Ish muhiti bo'yicha eslatmalar:** kompyuterda RAM kam (7.7 GB, ko'pincha 0.1 GB bo'sh) — fondagi dev serverlar o'zi o'chib qolishi mumkin;
  qayta yoqishdan oldin foydalanuvchidan so'ra. Brauzerda tekshirganda Chrome oynasi fonda bo'lsa video yuklanmaydi va animatsiya yurmaydi
  (`document.visibilityState === 'hidden'`) — shunda sahnani `?sinov=0.6` bilan ochib, blokka `el.style.setProperty('--p', 0.5)` qo'yib ko'r;
  sahifaning silliq aylantirgichi fondagi tabda `scrollTo` ni qaytarib yuboradi. Foydalanuvchi limitni tejayapti — qisqa va aniq ishla.
- **42-qism (reklama bosh sahifasi)**: 2026-10-11 da lusion.co/about ruhida qayta yozildi — **brauzerda hali ko'rilmagan** (xotira yetmay dev server
  o'chgan edi; faqat lint va build o'tgan). Yangi: baland bosh kadr (ulkan WEDDY so'z-belgisi harflari aylantirganda qayrilib ketadi, ortidan bayonot
  qatorlab chiqadi), `BoshVideo` (`public/video/bosh_keng|bosh_tor`, WebGL ustiga screen bilan), 0-sahnada zarrachalar chang (libos faqat yakunda),
  shapkada ovoz tugmasi + pill'lar + to'liq ekranli menyu, «+» to'r belgilari, tilla fonda 8 ta «o'yin kartasi», sanoqlar, tezlikka qarab qiyshayadigan
  lentalar, chaqiriq sahnasi, yorug' oyoq + «Tizimga kirish» tasmasi, silliq g'ildirak aylantirish, magnitli tugmalar, 3 holatli kursor, WebAudio ovoz (standart o'chiq).
  Tekshirish kerak: 1440×900 va 390×844 da har sahna, reduced-motion, WebGL'siz holat, forma yuborish. Eslatma: `docs/FRONTEND_HANDOFF.md` da aytilgan
  `BoshVideo` kodi diskda yo'q edi — shu qismda qayta yozildi. `ALOQA` bo'sh. Dev konsol: `__sahna.darhol(0..5)`, `__hisobla()`.
- **41-qism (tahrirlash/o'chirish amallari) brauzerda sinalmagan** — faqat API testlari, lint va build: xarajatni tuzatish/bekor qilish,
  kategoriya, tayyor chegirmalar ekrani, tarif tahriri, zakazda libos almashtirish va salonchi, filial/salonchi/doimiy xarajat/mavsumiy qoida formalari.
- **33–40-qismlar brauzerda sinalmagan** (faqat API testlari): filiallar va filial kassasi, dona ta'miri, dashbord filial tanlovi va havolalari,
  SMS bloki, integratsiyalar, zalog tekshiruvi, inkassatsiya, smenalar tarixi, xarajatlar ekrani, chegirma summada. 1–32-qismlarning aksari sinalgan.
- Haqiqiy xizmat bilan sinalmagan: Telegram, Eskiz (faqat soxta javoblar). Eskiz API yo'llari va Click/Payme havola formati xotiradan yozilgan.
- Manekin fonni ajratishi faqat sun'iy rasmlarda sinalgan (FT-5.6 sifat mezoni bajarilmagan).
- Oxirgi to'liq test: 580 tadan 579 (vaqt mintaqasi xatosi topildi va tuzatildi; keyin faqat finance + sozlamalar, 85 ta, qayta o'tkazilgan).
  Vaqtga bog'liq boshqa testlar bo'lishi mumkin.
- Faqat dev muhit: production (HTTPS, nginx, zaxira nusxa, S3-mos media saqlash) sozlanmagan; yuklama sinovi yo'q.
  Media hozir `backend/media/` da va DEBUG da ochiq; nginx `/media/` ga CORS berishi kerak (manekin eksporti).
- Dev bazada foydalanuvchining o'z sinov ma'lumotlari bor — tozalashda faqat o'zing yaratganni o'chir.

- **Chaqiriq sahnasi (2026-10-11, 19:30) — atlasmotion.com uslubida** (`Yakun.jsx` 3-sahna + `yakun.css` «3) Chaqiriq»). Shu kuni avval
  jjettas.com uslubidagi nuqtali yozuv/polaroid variantlari qilingan edi — foydalanuvchi so'rovi bilan to'liq almashtirildi.
  - Fon: `public/yakun/osmon.mp4` (+`osmon.jpg`) — kamera tilla bulutlardan saroyga tushadi; Kie'da yaratilgan (boshlang'ich kadr
    `generations/weddy_yakun-bulut_*.png`, video `weddy_yakun-fon_*.mp4`, Kling 3.0, 10 s, ≈140 kredit), 1600 kenglik, `-g 3` (zich kalit kadr).
    Video ijro etilmaydi: `Yakun.jsx` dagi effekt `currentTime` ni aylantirishga bog'laydi (bo'lim ekranga kirganidan yopishqoq sahna oxirigacha).
  - Yozuvlar (`--p` dan, CSS): kichik «Navbat sizda.» so'zma-so'z chiqib so'nadi → «SALONINGIZ / WEDDY'GA TAYYORMI?» harflari qator ostidan
    birin-ketin ko'tariladi (ikkinchi qator o'ngga surilgan va tilla) → izoh so'zlari xiradan yorqinga → «A'zo bo'lish». Shrift Manrope 800.
  - Sahna 540vh. `index.html` dan Anton shrifti olib tashlangan. Kie'da ≈380 kredit qolgan (hisobdan, tekshirilmagan).
  - Ko'rilgan: 1920 kenglikda to'rt nuqtada (bulutlar, harflar ko'tarilishi, izoh, oxiri) — video vaqti aylantirishga ergashadi.
    Ko'rilmagan: jonli aylantirish silliqligi, telefon, `prefers-reduced-motion` (bunda video birinchi kadrda qoladi).

- **Yakuniy qism tiklandi (2026-10-11) — uch sahna to'g'ri tartibda: Chaqiriq → Raqamlar → Kirish**. Foydalanuvchi so'rovi: «Saloningiz
  Weddy'ga tayyormi?» qismidan **keyin** guldastali slaydlar (Raqamlar) va to'liq ekranli video (Kirish) kelishi kerak — ular avvalgi
  «faqat Chaqiriq qoldi» ishida noto'g'ri olib tashlangan edi, endi qayta tiklandi.
  - `Yakun.jsx` yana uch sahnaga qaytdi: 1) **Chaqiriq** (`osmon.mp4` fon + «Navbat sizda.» + sarlavha + izoh + «A'zo bo'lish»,
    `data-t="5"`), 2) **Raqamlar** (markazda bitta ramkasiz gologramma guldasta + sanalgan raqamlar + lenta, fon `/tashvish/fon-1.jpg`),
    3) **Kirish** (`kirish.mp4` to'liq ekranli video). `gologrammaYarat` yana ishlatiladi (`gul` canvasi, `hol.current.tanla(...)` scroll'ga
    qarab faol guldastani almashadi).
  - `yakun.css` qayta yozildi: Chaqiriq osmon qoidalari saqlandi, unga `.rk-yk-kirish, .rk-yk-raqam { background: var(--yk-fon); }` va
    Raqamlar (bitta canvas) + Kirish qoidalari hamda to'liq media query (Chaqiriq + Raqamlar + Kirish mobile) qo'shildi. Tartib JSX'ga mos:
    Chaqiriq → Raqamlar → Kirish.
  - `Reklama.jsx` izohi yangilandi (endi uch sahna). `data-t` faqat Chaqiriq'da `="5"` — Raqamlar va Kirish WebGL fon shaklini o'zgartirmaydi
    (T 5 da qoladi), shuning uchun ularga `data-t` qo'shilmadi.
  - Build o'tdi (Vite 8.3.4). Tekshirilmagan: jonli aylantirishda uch sahnaning silliqligi va o'tishlari, telefon/tik ekran.

- **A'zo bo'lish qismi bezatildi (2026-10-11)**. Foydalanuvchi so'rovi: «azo bo'lish qismini sarg'aytir, orqa foniga bron video qo'y va
  ma'lumot kiritadigan blokni fonini shaffofroq qil».
  - `Reklama.jsx` dagi `.rk-azo` sahnasiga `<video class="rk-azo-video">` qo'shildi — `public/video/libos_bron.mp4` (+`libos_bron.jpg` posteri,
    `muted autoPlay loop playsInline preload="metadata"`).
  - `reklama.css`: `.rk-azo` ga `overflow: hidden`, video'ga to'liq qoplovchi qoida (`position: absolute; inset: 0; object-fit: cover`),
    `::before` bilan tilla bo'yash (`mix-blend-mode: color; linear-gradient(180deg, #d9a45f, #6b471c); opacity .72` — yakun.css'dagi usul),
    `::after` bilan chetlarni qoraytiruvchi radial gradient, matn va forma uchun `z-index: 1`. Media querydagi `.rk-azo > :first-child`
    selectori video birinchi bola bo'lib qolgani uchun `.rk-azo > .rk-azo-matn` ga tuzatildi (matn `justify-self: end` dan mahrum qolmasin).
  - `.rk-forma` foni shaffoflashtirildi: `rgba(253,250,245,.97)` → `rgba(253,250,245,.78)` + `backdrop-filter: blur(6px)`.
  - Build o'tdi (Vite 8.3.4). Ko'rilmagan: jonli brauzerda (ayniqsa 390×844 tor ekranda) video, tilla rang va forma shaffofligi.
  - **Takroriy so'rov (2026-10-11)** — sarg'ish filtr va shaffoflik yetarli ko'rinmagani uchun kuchaytirildi: video filtrida
    `sepia(.62)` → `sepia(.88) saturate(1.6) hue-rotate(-12deg) brightness(1.02) contrast(1.05)`; `.rk-azo::after` dagi quyuq ko'k parda
    iliq-qoramtir tilla yuvish qatlamiga almashtirildi (`linear-gradient(180deg, rgba(228,193,150,.4), rgba(204,152,102,.1))` ustiga);
    `.rk-azo .rk-forma` foni `.14` → `.08`, maydonlar `.2` → `.14`, blur `16px`. Build o'tdi.

- **Chaqiriq sarlavhasi EZAZ shriftiga, «Navbat sizda.» kattalashtirildi (2026-10-11)**. Foydalanuvchi so'rovi:
  «saloninggiz weddiyga tayyorni degan joyini shriftlarini ezaznikiga to'g'irla va endi sizning navbatingizni kattaroq qil».
  - `yakun.css` dagi `.rk-yk-chaqiriq h2` sarlavhasi Manrope'dan EZAZ serifiga o'tkazildi: `font-family: var(--serif)` (Casagrande Deco/Forum),
    `font-weight: 800` → `400`, `letter-spacing: -.035em` → `.02em`, `line-height: .94` → `1.04` (dekorativ serifga mos).
  - «Navbat sizda.» (`.rk-yk-kichik`) kattalashtirildi: `font-size: clamp(22px, 2.5vw, 46px)` → `clamp(30px, 4vw, 72px)` (shrift Manrope'da qoldi).
  - Bo'lim boshidagi shrift izohi yangilandi. Build o'tdi (Vite 8.3.4). Ko'rilmagan: jonli brauzerda serif sarlavha va kattalashgan yozuv.

- **Chaqiriq sahnasi to'liq EZAZ serifiga birlashtirildi (2026-10-11)**. Foydalanuvchi so'rovi:
  «navbar sizda va boshqa sozlarni ham shriftini bir hil qil» («Navbat sizda» typo).
  - `.rk-yk-kichik` («Navbat sizda.») va `.rk-yk-izoh` (izoh) ham sarlavha bilan bir xil EZAZ serifiga o'tkazildi:
    `font-family: var(--serif)`, `font-weight: 400`. Kichik yozuvda `letter-spacing: -.03em` → `.02em`, `line-height: .98` → `1.04`;
    izohda `font-weight: 700` → `400`, `letter-spacing: -.02em` → `.01em`, `line-height: 1.16` → `1.24`.
  - Endi Chaqiriq sahnasidagi barcha matn (kichik yozuv, sarlavha, izoh) EZAZ serifida; navbar/menyu shriftlari avvaldan serif edi.
    Build o'tdi (Vite 8.3.4).

- **Izoh matnidan «—» tire olib tashlandi (2026-10-11)**. Foydalanuvchi so'rovi: «bitta tizimda degan joyga tire kerak emas».
  `Yakun.jsx` dagi `IZOH`: «…kassa va hisobot — bitta tizimda.» → «…kassa va hisobot bitta tizimda.». Build o'tdi (Vite 8.3.4).

- **Futer bitta ko'k blokka yig'ildi (2026-10-11)**. Foydalanuvchi so'rovi: «futer qismidagi oq va ko'kni bitta qil, shakl oqda qolsin,
  rang ko'kniki; ichida icon va brend nomi chap tarafda, o'ng tarafiga "Saloningiz ulanganmi? Davom eting"; tagida katta yozuvda
  "Tizimga kirish" (kursor bilan yuruvchi knopka) va chetda yuqoriga strelka».
  - `Reklama.jsx` dagi oq `.rk-oyoq-yorug` bloki olib tashlandi; `.rk-oyoq` o'zi to'q ko'k (`var(--siyoh)`) fon oldi. `.rk-oyoq-bosh`
    (flex space-between): chapda `.rk-oyoq-brend` (`<Belgi />` + `WEDDY`), o'ngda `<small>Saloningiz ulanganmi?<br/>Davom eting</small>`.
  - Pastda `.rk-keyingi` — katta `Tizimga kirish` tasmasi, `data-magnit` (magnit) + `data-kursor="Kirish"` (halqa yozuvi) qo'shildi;
    strelka ichi `→` + tilla to'ldiriladigan `.rk-keyingi-yol` saqlandi. `.rk-tepaga` («↑») o'ng yuqori chetda shaffof oq halqa bo'ldi.
  - `.rk-keyingi-tor` (oq «+» to'r belgilari) `.rk-oyoq` darajasiga ko'chirildi (`bottom: 22px`). Tor ekranda (max-width 899px)
    `.rk-oyoq-bosh` ustma-ust (column) joylashadi.
  - Build o'tdi (Vite 8.3.4). Ko'rilmagan: jonli brauzerda, ayniqsa tor ekran (390×844).

- **A'zo bo'lish foni, «Weddy» videosi va futer (2026-10-11, 21:10):**
  - `Yakun.jsx` dagi uchinchi sahna (faqat «Weddy» yozuvli to'liq ekran video, `.rk-yk-kirish`) foydalanuvchi so'rovi bilan **olib tashlandi**
    (JSX, `video` ref, ijro effekti, `yakun.css` dagi «3) Kirish» bo'limi). `public/yakun/kirish.mp4|.jpg` diskda qolgan, ishlatilmaydi.
  - A'zo bo'lish (`Reklama.jsx` → `.rk-azo`): fon endi `public/yakun/bog.mp4` (+`bog.jpg`) — anime uslubidagi yomg'irli bog', ayvonda to'y libosi.
    Kie'da yaratilgan (kadr `generations/weddy_azo-bog_*.png`, video `weddy_azo-bog-video_*.mp4`, ≈82 kredit); ffmpeg `xfade` bilan boshi-oxiri
    ulanib 4 s lik uzluksiz halqa qilingan. Tilla `mix-blend-mode: color` pardasi olib tashlandi (anime ranglarini o'ldirardi); o'rniga
    `.rk-azo::after` da chapdan va pastdan to'q ko'k parda. Bo'lim `min-height: 100svh`. Forma kartasi ayvondagi libosni yopib turadi.
  - Futer (`.rk-oyoq`) qayta chizildi: tepada tilla chiziq, brend + tavsif va ikki ustun havola («Sahifa», «Tizim»), o'rtada yorliqli katta
    «Tizimga kirish», pastda tasma (© yil, «Tepaga» tugmasi). Eski `rk-oyoq-bosh`, `rk-oyoq-havola`, `rk-keyingi-tor` olib tashlandi.
  - Ko'rilgan: 1920 kenglikda a'zo bo'lish (poster bilan) va futer. Ko'rilmagan: fon videosining ijrosi va halqa tutashuvi (sinov tabi fonda
    edi), telefon. Kie'da ≈300 kredit qolgan (hisobdan, tekshirilmagan).

- **Guldasta, a'zo bo'lish tusi, forma va futer (2026-10-11, 21:20) — KO'Z BILAN TEKSHIRILMAGAN** (sinov oynasi yig'ib qo'yilgan edi, 0×0):
  - Guldasta sahnasi (`Yakun.jsx` «Raqamlar»): gologramma kanvasi endi butun sahnani egallaydi (`.rk-yk-gul-qator { inset: 0 }`), figura o'lchami
    `gologrammaYarat(..., undefined, { markaz: [.5, .5], masshtab: .19 })` bilan beriladi. Sabab: kanvas 40vh kvadrat edi — almashishda sochilgan
    nuqtalar to'rtburchak chetda kesilardi. `gologramma.js` ga 4-parametr qo'shildi (standart qiymatlar eski — «Kelinlar» o'zgarmaydi).
  - A'zo bo'lish: fon videosiga sarg'ish-tilla tus (`.rk-azo-video` → `filter: sepia(.62) ...`); forma shaffof oyna
    (`.rk-azo .rk-forma`: fon 14%, blur 14px, oq yozuv, yarim shaffof maydonlar, tilla tugma).
  - Futer ixchamlandi: faqat logo, katta «Tizimga kirish», pastda «© yil · Platforma egasi · ↑». Tavsif va havola ustunlari olib tashlandi.
    «Platforma egasi» qoldirilgan — platforma egasi paneliga yagona kirish yo'li.
  - `Kelinlar.jsx`: `yol > 0` himoyasi qo'shildi — oyna o'lchamsiz (0×0) bo'lganda 0/0 = NaN indeks butun sahifani qulatardi.
  - Tekshirilgan: lint, build, sahifa DOM da to'liq chiziladi, hisoblangan uslublar kutilgandek. **Birinchi ish: shu to'rttasini ekranda ko'rish.**

- **Kelinlar foni platforma ichki sahifalariga (2026-10-11) — KO'Z BILAN TEKSHIRILMAGAN**:
  - Bosh sahifadagi «Kelinlar» bo'limi qasr foni (`/kelinlar/saroy.jpg` + aura) va tepadan tushayotgan tilla harflar yomg'iri
    platformaning barcha ichki sahifalari (Dashbord, Bosh, Yangi zakaz, Zakazlar, Mijozlar, Kalendar, Katalog, Kassa, Hisobot, Sozlama)
    orqa foniga qo'llandi.
  - Yangi fayllar: `pages/PlatformaFon.jsx` (fon qatlami), `pages/platforma-fon.css`, `pages/yomgir.js` (`yomgirYarat` Kelinlar.jsx dan
    ajratib chiqarildi — ikkala joyda ishlatiladi). `App.jsx` da `.ilova` ichiga `<PlatformaFon />` qo'shildi; `index.css` da `.yuqori`
    header matni fil suyagi rang (`#fbf6ee`) qilindi (to'q fonda o'qilishi uchun).
  - Qatlam kontent ORTIDA turadi: `position: fixed; z-index: -1; pointer-events: none` — kontent kartochkalari (oq fonli) to'q fonda
    ajralib turadi, ichidagi `position: fixed` modallar (vitrina, rasm-oyna, hujjat, manekin) o'z z-indexlari bilan ishlashda davom etadi.
  - `npm run build` muvaffaqiyatli o'tdi. **Birinchi ish: ekranda ko'rish** — telefon/tik ekronda (390×844) va `prefers-reduced-motion`
    rejimida (canvas yashiriladi) tekshirilmagan.

- **Ichki sahifa bloklari/knopkalari/formalari shisha (glassmorphism) uslubiga (2026-10-11) — KO'Z BILAN TEKSHIRILMAGAN**:
  Foydalanuvchi so'rovi: «barcha sahifalardagi bloklar knopkalarni boshsahifadagi a'zo bo'lishdagi ma'lumot kiritish blokinikiday qil
  stilini». Bosh sahifadagi a'zo bo'lish formasi (`reklama.css` → `.rk-azo .rk-forma`) uslubi platformaning barcha ichki sahifalari
  (Dashbord, Bosh, Yangi zakaz, Zakazlar, Mijozlar, Kalendar, Katalog, Kassa, Hisobot, Sozlama) elementlariga qo'llandi.
  - `index.css` da (~30+ edit): input/select/textarea — shaffof oq fon (`rgba(255,255,255,.14)`), oq chet (`rgba(255,255,255,.32)`),
    tilla focus (`border-color: var(--tilla)` + `box-shadow 0 0 0 4px rgba(228,193,150,.22)`); `button` — tilla gradient
    (`linear-gradient(110deg, var(--tilla-toq), var(--tilla))`) + to'q matn (`var(--siyoh)`); `button.ikkinchi` — shisha shaffof.
  - Kartochkalar (`.blok`, `.liboslar li`, `.qator-btn`, `.dona`, `.guruh`, `.kalendar-ora`) — `rgba(253,250,245,.08)` + `blur(12px)`
    + oq ichki chiziq; `.pastki` nav va `.jami` — to'q shisha (`rgba(14,26,43,.72-.78)` + `blur(16px)`), faol nav tugmasi tilla.
  - To'q qasr fonida ko'rinmay qolgan ranglar almashtirildi: matnlar/chegaralar `var(--tilla)` yoki fil suyagi (`#fbf6ee`), xiralashgan
    yozuvlar `rgba(251,246,238,.55)`, xato/qizil `#ffb4ab`; binafsha `--rang` faqat oq fonli modallarda (vitrina, hujjat, manekin) qoldi.
  - `npm run build` muvaffaqiyatli o'tdi (faqat mavjud chunk-size ogohlantirishi). **Birinchi ish: ekranda ko'rish** — ayniqsa oq fonli
    modallar ichidagi matn kontrasti va telefon/tik ekranni tekshirish.

- **Pastdagi nav → chap tarafdagi panel/sidebar (2026-10-11) — KO'Z BILAN TEKSHIRILMAGAN**:
  Foydalanuvchi so'rovi: «foydalanuvchi profiliga kirganda pastda bosh sahifa yangi zakaz kabi menu bo'lib qolar ekan. shu kabi
  sahifalarni chatgptnikiday chap tarafdagi paneldan kerakli bo'lim tanlanadi, bo'lim ichidagilari o'rtaga chiqadigan qil».
  Yechim: faqat CSS orqali, `App.jsx` strukturasiga tegilmagan (nav buttonlari va `bolimlar` massivi o'zgarmadi).
  - `index.css` oxiriga `@media (min-width: 768px)` qo'shildi: keng ekranda `.pastki` — `position: fixed; top:0; bottom:0; left:0`,
    `width: 240px`, `flex-direction: column` (vertikal chap panel); `.ilova` ga `padding-left: 240px` (kontent o'ngga); `.pastki button`
    — to'liq kenglik, chapga tekislangan, faol holati tilla gradient; `.jami` sticky qismi `bottom: 0` ga olindi (pastda nav yo'q).
  - Tor ekranlarda (telefon, < 768px) avvalgi pastdagi nav saqlanib qoldi — mobil UX buzilmadi.
  - `npm run build` muvaffaqiyatli o'tdi. **Birinchi ish: ekranda ko'rish** — desktop (≥768px) da chap panel ko'rinishi, faol bo'lim
    tilla ajratilishi va mobil (<768px) da pastdagi nav avvalgidek ishlashi.

- **«Libosa raqamlarda» kirish effekti boshqa sahnalarga (2026-10-12) — KO'Z BILAN TEKSHIRILMAGAN**: sahna ekranni to'liq egallamaguncha
  faqat qorong'ilik va sarlavha, keyin kontent yorishib ochiladi (`--kir` = `--p` dan). `Kelinlar` (`kelinlar.css`, `.rk-kel-yopishqoq::after`),
  `Imkoniyatlar` (`tashvishlar.css`, `.rk-tv::after`; birinchi kadr skaneri endi `threshold: .98` da, ya'ni to'liq egallaganda), `Chaqiriq`
  (`yakun.css`, fon video `opacity: var(--kir)`). `npm run build` o'tdi. Birinchi ish: jonli aylantirib tezlik/silliqlikni ko'rish.

## Qolgan ishlar
Qiymat kiritish (Sozlama → «Integratsiyalar»; kiritilmasa ham tizim ishlaydi): Telegram bot tokeni; Eskiz hisobi + shablonlarni tasdiqlatish;
Click/Payme ID lari (bitta sinov to'lovi bilan tekshirish); soliq foizi; manekin sezgirligi (salonning haqiqiy rasmlari bilan).

Kod bilan:
1. 33–41-qismlarni brauzerda ko'rib chiqish va topilgan xatolarni tuzatish — **eng birinchi ish**.
2. Commit (foydalanuvchi so'raganda).
3. Click/Payme webhook (avtomatik tasdiqlash) — merchant sinov muhiti kerak.
4. Manekin rasmini bot orqali mijozga yuborish (FT-5.4); manekinda aksessuar joylashuvi libosga qarab alohida emas.
5. Instagram, 1C, onlayn kassa bilan avtomatik almashinuv (3-bosqich).
6. Production tayyorgarligi.

Reklama sahifasi (43–44-qism davomi):
- **2026-10-13: reklama sahifasining telefon ko'rinishi (390×844, brauzerda iframe orqali ko'rib sozlangan):**
  - «Imkoniyatlar» slayderi (`tashvishlar.css`, telefon `@media`): kelin tepada havoda turardi — endi o'ngda, matn yonida, fondagi polda
    (`left: 77%`, oyog'i `100svh - 124px`, bo'yi `min(52svh, 116vw)`); matn (sarlavhadan tashqari) `max-width: 58%`; qoraytirish faqat matn ortida.
  - Chaqiriq sarlavhasi (`Yakun.jsx` `SARLAVHA`, `yakun.css`): «tayyormi?» ekranga sig'may kesilardi — sarlavha uch bo'lakka bo'lindi;
    keng ekranda avvalgidek ikki qator, telefonda uch qator.
  - Oyoq (`reklama.css`, `@media (max-width: 759px)`): logo va «Tizimga kirish» bitta qatorda, balandligi 211 → 111 px.
  - Shapka (`reklama.css`, o'sha `@media`): logo 17 px, ovoz tugmasi va «Menyu» 46 → 36 px, chet bo'shlig'i 22 → 14 px; menyu ochilish doirasi markazi moslandi.
  - Chaqiriq sarlavhasi telefonda keyin «tartibsiz» qilindi (2-qator `1.5em`, 3-qator `.55em` surilgan), shrift `clamp(24px, 8.8vw, 64px)`.
  - A'zo bo'lish bo'limi va ariza formasi (`reklama.css`, o'sha `@media`): matn, bo'shliqlar va maydonlar kichraydi — bo'lim 1115 → 844 px (bitta ekran).
  - **Ilova ichki tomoni (rahbar, xodim, platforma) telefonda** — `index.css` oxiridagi `@media (max-width: 767px)` bloklari, 390×844 da
    demo `ezaz` salonida rahbar bo'lib va platforma panelida ko'rib chiqilgan (xodim roli alohida ko'rilmagan — sahifalari bir xil):
    - **Shapka va menyu (foydalanuvchi so'rovi: «bosh sahifanikiday tepada logo va chapda menyu»):** yangi `components/Shapka.jsx` —
      telefonda tepada yopishqoq shapka: chapda dumaloq «menyu» tugmasi va LIBOSA logosi, o'ngda xodim ismi va «Almashtirish».
      Pastki tugmalar qatori yo'q: `.pastki` telefonda chapdan chiqadigan menyu (`.ochiq`, orqasida `.menyu-parda`), holati `App.jsx` va
      `Platforma.jsx` dagi `menyu`. Bo'lim tanlansa yopiladi, «← Orqaga» da ochiq qoladi. Sozlama bo'limlari ham shu menyuda ko'rinadi.
      Keng ekranda o'zgarish yo'q (tugma va logo yashirin). Platformada yangi shapka brauzerda ko'rilmagan — faqat salon tomonida tekshirilgan.
    - Formalar ixcham: maydon/tugma ichki bo'shliqlari, oraliqlar, `main` va `.blok` chetlari kichraydi (maydon yozuvi 16px qoldi).
    - `.qator`: maydonlar torayadi, sig'magan tugma keyingi qatorga tushadi (Katalog «Rang» maydoni va Platforma «Sanalarni saqlash» ekrandan chiqib ketardi).
    - `.blok > .qator-btn:first-child` ramkasiz (Katalogda «karta ichida karta» edi); `.sozlama-saqlash` pastki nav ortida qolmaydi (`bottom: 60px`).
    - `.tasdiq a` tilla rangda (Platforma «So'rovlar» dagi telefon havolasi to'q ko'k edi) — bu qoida barcha ekranlarga tegishli.
  - Yakuniy qismning qolgan sahnalari (Raqamlar, Kirish) telefonda hali alohida ko'rib chiqilmagan.
- Yakuniy qismni jonli aylantirib ko'rish (silliqlik, sahnalar orasidagi o'tish); foydalanuvchi fikriga qarab sozlash.
- Foydalanuvchi oxirgi so'rovlarda sozlagan narsalar (yana so'rashi mumkin): slayderda kelin o'rni (`SLAYDLAR` → `x`, `y`, `h`), slayd qadami (55vh).
  (Guldasta qatori, raqamlar va kirish videosi qayta tiklandi — 2026-10-11 dagi «Yakuniy qism tiklandi» ishiga qarang.)
- `qasr.mp4` ni qayta kodlash: `ffmpeg -i qasr.mp4 -an -c:v libx264 -g 1 -crf 20 -pix_fmt yuv420p -movflags +faststart qasr_intra.mp4`, keyin almashtir;
  posterni ham yangila: `ffmpeg -ss 4.3 -i qasr.mp4 -frames:v 1 -q:v 3 qasr-poster.jpg`. Video 480p qoralama — 1080p versiyasi kerak bo'lishi mumkin.
- Tozalash (faqat foydalanuvchi so'rasa): `OyinKartalar.jsx`+`kartalar.css`, `BoshVideo`, `reklama.css` dagi ishlatilmay qolgan uslublar
  (`rk-galereya`, `rk-karta`, `rk-raqam*`, `rk-lenta`, `rk-qanday`, `rk-qadam*`, `rk-rol*`, `rk-chaqiriq`), ishlatilmaydigan videolar.
- `docs/PROGRESS_ARXIV.md` ga 44-qismning batafsil bayoni **qo'shilmagan** — kerak bo'lsa shu fayldagi «44-qism» bo'limidan ko'chir.

Ochiq savol: soliq qaysi oyga tushishi — buxgalter xulosasi kutilmoqda (hozir tushum tan olingan oyga).

## Bu faylni yuritish
Qisqa tut: yangi ish tugagach tegishli bo'limni yangila (jadval, qoidalar, tekshirilmagan, qolgan ishlar) va test sonini o'zgartir.
Batafsil bayonni `docs/PROGRESS_ARXIV.md` oxiriga qo'sh.
