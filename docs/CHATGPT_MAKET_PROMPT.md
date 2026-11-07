# ChatGPT uchun dizayn-maket prompt'lari (Libosa ichki paneli)

> Qanday ishlatiladi: 1) ChatGPT'da yangi suhbat oching, **0-prompt**ni yuboring va o'zingizdagi «DressRent Pro» maketini
> (rasm) uslub namunasi sifatida biriktiring. 2) Shu suhbatning o'zida sahifa prompt'larini **birma-bir** yuboring — har biri uchun
> **bitta rasm** (bitta rasmga ko'p sahifa sig'dirilsa, yozuvlar o'qilmaydi). 3) Tayyor rasmlarni menga bering: men ularni
> brauzerda ko'rik bazasi bilan yonma-yon solishtirib, ishlaydigan dasturga o'tkazaman.
> Prompt'lar ingliz tilida (ChatGPT shunda yaxshi tushunadi), interfeys yozuvlari esa o'zbekcha — qo'shtirnoq ichidagisini aynan shunday yozdiring.

---

## 0-prompt — umumiy uslub (birinchi yuboring)

```
I am designing a desktop web app for a bridal-dress rental salon called "Libosa". Create high-fidelity, Figma-style UI mockups.
One screen per image, 1440x900 desktop frame, crisp and readable text, no lorem ipsum, no English UI labels.

VISUAL LANGUAGE (keep it consistent on every screen):
- Deep midnight-navy "frosted glass": translucent panels, 1px subtle light borders, 14-16px radius, soft backdrop blur.
  Behind everything a very dark, blurred image of an empty grand ballroom with a bride faintly visible.
- Accent: soft gold #E4C196. Text: warm off-white. Secondary text: blue-grey #8A93A3.
- Status colors (soft, low-saturation pills): green #7ED6A0 = booked/ok, blue #8DB4E8 = at customer, amber = waiting, red #FF9B92 = debt/late, pink #E9A6C4 = accent tile.
- Typography: serif "Forum" for headings and big numbers, "Spectral" for body text, italic "Cormorant Garamond" for small labels above numbers.
- Icons: thin line icons inside soft 52px rounded tiles tinted gold/green/blue/pink at ~14% opacity.
- Reference image attached = the layout rhythm I want (cards grid that fills the whole width, no empty side areas, equal 16px gaps).

APP SHELL (same on all screens): left sidebar 240px (logo "LIBOSA" + "Nafislik salon", items: Dashboard, Kassa, Liboslar, Zakazlar, Mijozlar, Hisobotlar, Sozlama,
with the active item marked by a thin gold bar). Top bar: page title on the left, wide search field "Zakaz: raqam, telefon yoki ism", bell icon with red count badge, user chip "Nodira · Rahbar".

DATA STYLE: realistic Uzbek data. Names: Dilnoza Karimova, Nodira Yusupova, Malika Rahimova, Sabina Usmonova. Money: "2 500 000 so'm". Dates: "12 noyabr". Dress names: Mira, Bella, Elsa, Luna, Rubin.
Reply "OK" and wait for the first screen.
```

---

## 1. Rahbar Dashboard

```
Screen 1: Dashboard (owner view). Layout, top to bottom:
Row 1 - four equal KPI cards, each: tinted icon tile on the left, italic small label, big serif number, one grey line of detail, a small up/down percent pill top-right:
"Tushum" 175 300 000 so'm (up 90%), "Yangi zakazlar" 77 (up 60%), "Bo'sh liboslar" 17 / 25, "Mijozlar" 51 (down 18%).
Row 2 - three cards, widths about 512 : 479 : 277:
 (a) "Tushum dinamikasi": big total, small italic "oldingi 30 kun - uzuq chiziq", gold area line chart with a dashed grey previous-period line, a small dropdown "30 kun" in the card header.
 (b) "Eng ko'p ijaraga berilgan": three portrait dress photo cards with rank badges #1 #2 #3, name, "Ijara: 9 marta", price.
 (c) "Yaqin bronlar": 5 rows - round initials avatar, bold customer name, grey "#79 - Mira", date on the right, green pill "Bron"; link "45 ta".
Row 3 - four cards, widths about 345 : 302 : 351 : 263:
 (a) "Bugun kassada" amount and 3 small lines; (b) "Liboslar holati": donut with the number 25 in the middle and a legend (Bo'sh, Mijozda, Tozalashda, Ta'mirda with counts and percents);
 (c) "Nazorat": three mini rows "Kassada kamomad - Yo'q", "Diqqat - 1 ta", "Liboslar joyidami - Sanalmagan" with check/warning icons;
 (d) "Tezkor amallar": 2x2 tiles "Yangi zakaz", "To'lov qabul", "Libos qo'shish", "Hisobotlar".
```

## 2. Sotuvchi (xodim) bosh sahifasi

```
Screen 2: Home screen for a salesperson (no owner statistics). Title "Bugungi ishlar". Masonry of task cards, each with an icon, title, a count pill and up to 4 rows (avatar, name, "#13 - Mira", right side amount or status pill):
"Bugun olib ketadi" (2) with "Qoldiq 1 200 000 so'm" amber pills, "Bugun qaytaradi" (1) with blue pill "mijozda", "Kechikkan" (1) red card with "3 kun" pill,
"Qo'ng'iroq qilish" (3) with "Bog'landim" buttons, "Qoldiq to'lanmagan" (5). Above them a thin amber banner "Smena ochiq emas - to'lov qabul qilib bo'lmaydi" with button "Kassaga o'tish". Sidebar has fewer items (no Hisobotlar, no Sozlama).
```

## 3. Zakazlar ro'yxati

```
Screen 3: Orders list. Page tabs under the top bar: "Ro'yxat" (active) and "Bandlik kalendari".
Row of four clickable KPI-filter cards: "Bugun olib ketadi 1 (ertaga - 0 ta)", "Bugun qaytaradi 0", "Kechikkan 0", "To'lov kutmoqda 3".
Below, two columns: left (wide) a glass card with filter tabs "Faol 8 | Vaqtinchalik 2 | Bron 6 | Berildi | Qarz bor | Yopilgan 2 | Bekor 3 | Hammasi 13", search field and a gold button "+ Yangi zakaz".
Table rows: small dress photo, bold "#13 Zalog Sinov", grey "Libos Mira", round phone button, rental dates "8 - 9 noyabr" with a small gold note "bugun olib ketadi", status pill (Bron/Berildi/...), payment progress bar with "To'liq" or "0,4 mln / 2 mln", total on the right "2 000 000 so'm".
Right column (340px): card "Bugun" with sections "Olib ketadi", "Qaytaradi", "Kechikkan", each a few avatar rows.
```

## 4. Zakaz kartasi (batafsil)

```
Screen 4: Order detail page, designed like an elegant paper invitation card ("varaq") on the glass background.
Top: back arrow, "#13 Zalog Sinov", status pill. A thin gold thread with 4 nodes: "Bron - To'lov - Berildi - Qaytdi" (current node highlighted, caption under it).
Left, the paper card: large serif rental dates "8-9 noyabr", customer name and phone, the dress with photo and price, price breakdown rows ("Asosiy narx", "Ustama", "Chegirma", bold "Jami"), 
"To'lovlar" timeline (Avans - Naqd, Qoldiq - Terminal, with times and who accepted), "Zalog" row.
Right column: one big gold primary action button ("Libosni berish"), secondary buttons ("Sanani ko'chirish", "Libosni almashtirish", "Chegirma so'rash", "Bekor qilish"), 
document chips "Shartnoma", "Kvitansiya", "Dalolatnoma", and a "Tarix" vertical timeline.
```

## 5. Yangi zakaz (3 qadam)

```
Screen 5: New order wizard, step 2 of 3. Top thread: "Sana - Libos - Mijoz" (step 2 active, step 1 done with a check).
Main area: filter chips (category, size), grid of portrait dress cards (photo, name, size, price, small green "Bo'sh" or red "Band" label; selected card has a gold border and check).
Right sticky paper card "Zakaz varaqasi": dates, selected dresses list, price lines, bold total, gold button "Davom etish".
```

## 6. Liboslar

```
Screen 6: Dress catalog. Page tabs "Ro'yxat", "Aksessuarlar", "Sanoq", "Yetkazib beruvchilar".
Four KPI-filter cards: "Faol liboslar 25 (o'rtacha ijara 1,5 mln)", "Ijaraga tayyor 17", "Mijozda 4 (eng yaqin qaytishi 14.11)", "Ta'mir va tozalashda 4".
Below: left filter column (250px) with groups "Kategoriya" (Hammasi, Milliy, Zamonaviy... with counts), "O'lcham" (chips 42 44 46 48), "Holat" (rows with counts), link "Filtrlarni tozalash".
Right: grid of tall 2:3 dress photo cards, each with name, article code, category and size, price, a status ribbon on the photo; search, "Kategoriyalar" and gold "+ Libos qo'shish" in the card header.
```

## 7. Mijozlar

```
Screen 7: Customers. Tabs "Mijozlar" and "Salonchilar". Four KPI-filter cards: "Jami mijozlar 51", "Yangi mijozlar (30 kun)", "Yaqin to'ylar", "Qarzdorlar" (red).
Table card: tabs "Hammasi | Qora ro'yxat", search "Telefon yoki ism"; rows with initials avatar, name, "+998 90 123 45 67", "To'y sanasi", "Zakazlar 3 ta - keyingisi 12.12.2026", total "4 500 000 so'm".
Also design the customer detail on a second frame: big serif wedding date with "30 kun qoldi", measurements tiles (Ko'krak, Bel, Son, Bo'y), order history list, buttons "Yangi zakaz" and "Qora ro'yxatga".
```

## 8. Kassa (POS)

```
Screen 8: Cash desk "To'lov qabul". Left sidebar switches to a Kassa sub-menu: Yangi zakaz, To'lov qabul (active), Xarajat, Inkassatsiya, Zaloglar, Smena hisoboti, Smenalar tarixi.
Top strip: green dot "Smena ochiq - Sotuvchi", and a gold-bordered chip "Sizda naqd 1 990 000 so'm".
Main: left list of orders waiting for payment (avatar rows with amount due), right payment panel: order summary, method toggle "Naqd | Terminal | O'tkazma", large amount display, quick buttons "To'liq" "50%", big numeric keypad 3x4 (tablet friendly), gold button "Qabul qilish - 1 000 000 so'm".
Second frame: "Smena hisoboti" - four KPI cards (Kassada naqd, Kirgan naqd, Terminal, Chiqim), below two cards: "Kun yakuni" checklist and "Naqd pul hisobi" ledger with a big gold "Hisobdagi qoldiq".
```

## 9. Hisobotlar

```
Screen 9: Reports. Sidebar switches to a Hisobotlar sub-menu (Umumiy hisobot, Oylik foyda active, Xarajatlar, Sotuvchi bonusi, Bank solishtirish).
"Oylik foyda": month picker "Noyabr 2026" with arrows; four KPI cards (Tushum with up-pill and "Oktabr 2026, 1-8: 0 so'm", Xarajatlar, Foyda, Foyda ulushi 100%);
numbered ledger rows (1 Kirgan pul, 2 Mijozlarga qaytarilgan, 3 Tushum, 4 Jarimalar, 5 Xarajatlar, 6 Foyda in large gold); below a 12-month bar chart "Oxirgi 12 oy".
Second frame: "Umumiy hisobot": report-type dropdown, period chips "Shu oy | O'tgan oy | Shu chorak | Shu yil", date range, KPI cards with comparison pills, data table with a totals row.
```

## 10. Sozlama

```
Screen 10: Settings overview "Barcha sozlamalar". Sidebar switches to a Sozlama sub-menu. Search field "Qidirish: PIN, SMS, artikul, filial...".
Six cards in a 3-column grid, each with a group title and 2-5 rows (rounded icon tile, bold name, grey one-line hint, chevron):
"Zakaz qoidalari" (Bron va zalog, Kechikish jarimasi, Avans qaytarish, Shartnoma bandlari), "Narx va chegirma" (Mavsumiy narx, Tayyor chegirmalar, Promokodlar), "Liboslar", "Salon va xodimlar" (Xodimlar, Sotuvchi bonusi, Kassa, Filiallar, Rekvizitlar),
"Ko'rinish va xabarlar" (Dashboard va hisobot, SMS eslatma, Integratsiyalar), "Xavfsizlik" (Qurilmalar va parol, Texnik yordam, Jurnal).
Second frame: one form section "Avans qaytarish" with radio options, a worked example line "3 000 000 lik zakazda 30% -> avans 900 000", and a sticky bottom bar "Saqlanmagan o'zgarishlar bor - Bekor qilish / Saqlash".
```

## 11. Kirish ekrani va qo'ng'iroqcha

```
Screen 11: Staff login on a tablet-style centered layout: salon name, row of staff cards with round photos and role under the name (Nodira - Rahbar, Malika - Sotuvchi, Dilnoza - Kassir), after choosing one a PIN pad with 4 dots and a 3x4 keypad.
Screen 12: the notification bell dropdown (340px) over a dimmed dashboard: sections "Salonni sozlash 3/4" (thin progress bar), "Qaroringiz kerak" (two rows with "Rad etish" / "Tasdiqlash" buttons), a list of notifications with colored dots, and at the bottom "Telegram ulash".
```

## 12. Telefon (390x844) — bir xil uslub

```
Screen 13-15: phone versions (390x844) of Dashboard, Zakazlar and Zakaz kartasi. Bottom tab bar with 5 items: Dashboard, Zakazlar, a round gold "+" button in the middle, Kassa, Ko'proq.
KPI cards in a 2x2 grid, lists as full-width rows, the same midnight-glass look, thumb-friendly 44px targets.
```

---

### Maslahat
- Har rasmdan keyin ChatGPT'ga ayting: «matnni aynan qo'shtirnoq ichidagidek yoz, imlo xatosi bo'lmasin». O'zbek harflari (o', g') ba'zan buziladi.
- Yoqmagan joyni aniq yozing: «3-qator kartalari tor, kengroq qil», «rang juda yorqin» — «yaxshila» emas.
- Eng muhim sahifalar: 1 (Dashboard), 3 (Zakazlar), 4 (Zakaz kartasi), 8 (Kassa). Avval shularni oling.
