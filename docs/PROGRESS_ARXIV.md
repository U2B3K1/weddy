# PROGRESS — Weddy

TZ manbasi: `TZ_Kelin_liboslari_saloni_v1.2.docx` (Desktop). Kod shu TZ versiyasiga mos.

## Ishga tushirish
```bash
docker compose up -d db                 # PostgreSQL 16, port 5433 (5432 lokal postgres band)
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py demo_ezaz   # demo salon
.venv/Scripts/python manage.py runserver
.venv/Scripts/python manage.py test        # 580 ta test
cd ../frontend && npm install && npm run dev
```

## Bajarildi (1-bosqich, 2026-10-09)
- Django 5.2 + DRF, PostgreSQL (`btree_gist`), React + Vite skeleti.
- **tenants**: `Salon`, `Xodim` (PIN), `IshonchliQurilma`; salon logini → qurilma tokeni → PIN → xodim tokeni;
  5 xato PIN = 15 daqiqa blok (FT-1.1, FT-1.7, FT-22.2). Abstract `SalonModel` (FT-22.4).
- **catalog**: `Kategoriya`, `Libos` (artikul salonda noyob, bufer kun: libos > kategoriya > standart).
- **bookings**: `Bron` + `ExclusionConstraint` (ikki marta bron bazada to'xtatiladi, FT-2.7),
  `bosh_liboslar` (FT-2.2, 2.3, 2.4), vaqtinchalik bron (FT-2.5).
- Testlar: Ilova D S01, S02, S03 (baza darajasida), S24, S27 + PIN bloklash.
- Frontend: salon kirishi, xodim tanlash + PIN, sana bo'yicha bo'sh liboslar.

## Bajarildi (davomi)
- **bookings**: `LibosQulfi` (15 daqiqa, FT-2.7): `POST /api/bronlar/qulf/`; zakaz saqlashda boshqa xodim qulfi hisobga olinadi.
- **orders**: `Mijoz` (telefon salonda noyob, qora ro'yxat), `Zakaz`, `ZakazPozitsiya`; `zakaz_yaratish` — barcha liboslar
  atomik band qilinadi yoki hech biri; raqam salonda ketma-ket; `narx_hisobla` (FT-4.3, Ilova C.3 raqamlari testda).
- API: `POST /api/zakazlar/`, `GET /api/mijozlar/qidirish/?telefon=` (tarix + qora ro'yxat, FT-2.9).

## Bajarildi (3-qism)
- Frontend zakaz formasi: telefon (mijoz tarixi/qora ro'yxat) → sanalar → libos tanlash (qulf bilan) → saqlash.
  Qulflangan libosda «Hozir boshqa sotuvchi rasmiylashtiryapti» belgisi (FT-2.7).
- **cash**: `Smena` (salonda bitta ochiq, DB cheklovi), `SmenaIshtirokchi`, `Tolov` (avans/qoldiq/jarima/zalog/
  zalog_qaytarish/vozvrat/xarajat/inkassatsiya); avans bronni mustahkamlaydi, to'liq to'lov `tolangan_sana` ni qo'yadi;
  `kassa_hisobot` (Ilova C.2), sotuvchi almashuvi (S12), farq bo'lsa izoh majburiy (S11).
- API: `/api/kassa/smena/` (+`ochish`, `qoshilish`, `chiqish`, `yopish`), `/api/kassa/tolovlar/`.

## Bajarildi (4-qism: zalog, berish, qaytarish)
- **orders**: `Zalog` (pul/hujjat/tillo, raqamli yorliq), `QaytarishAkti`; `rental.py`:
  - `libos_berish`: faqat bron holati, qoldiq to'liq to'langan va zalog olingan bo'lsa (FT-7.1, FT-7.6); pul zalogi kassaga kirim.
  - `libos_qaytarish`: jarima avval pul zalogidan ushlanadi, qolgani qarz; hujjat/tillo jarima to'lanmaguncha qaytmaydi (FT-7.3);
    tillo og'irligi qayta tortiladi (±0,1 g, S08); kechikish jarimasi (FT-9.3); baho 1–5; libos «Tozalashda» (FT-9.4).
  - Kassada: zalog qaytarish — chiqim, ushlab qolingan jarima — tushum (4.12 qatorlari to'g'ri chiqadi).
  - `qarzni_tolash`, `tozalash_tugadi`.
- API: `POST /api/zakazlar/<id>/berish|qaytarish|qarz-tolash/`, `POST /api/liboslar/<id>/tozalandi/`.
- Hali yo'q: dalolatnoma PDF (FT-7.4), kechikish jarimasi sozlamasi (hozir parametr), zalog rasm yuklash, frontend ekranlari.

## Bajarildi (5-qism: chegirma, 4.11)
- **orders**: `TayyorChegirma`, `ChegirmaSorovi` (jurnal: sotuvchi, sabab, rahbar qarori, FT-11.5); `discounts.py`:
  - `tayyor_chegirma_qollash` — tasdiqsiz, darhol (FT-11.7, S26);
  - `chegirma_sorash` — zakaz «Chegirma tasdig'i kutilmoqda», bron saqlanadi, avans qabul qilinmaydi (FT-11.2, 11.3);
  - `chegirma_qarori` — faqat rahbar; so'ralganni o'zgartirib tasdiqlash (10% -> 5%, FT-11.4), rad etilsa chegirmasiz narx.
  - Bitta zakazga bitta chegirma; avans olingan zakazga chegirma berilmaydi. Narx ustama qo'shilgan summadan (Ilova C.3).
- API: `POST /api/zakazlar/<id>/chegirma/`, `GET /api/chegirma-sorovlari/` (rahbar), `POST .../<id>/qaror/`,
  `GET|POST /api/tayyor-chegirmalar/` (POST — rahbar).
- Hali yo'q: «tasdiq kutilganda shartnoma/kvitansiya chop etilmaydi» (shartnoma moduli yo'q), promokodlar (3-bosqich),
  rahbarga Telegram xabar (2-bosqich), frontend ekranlari.

## Bajarildi (6-qism: zakazni o'zgartirish va bekor qilish, 4.17)
- **orders/changes.py** (hammasi atomik, xato bo'lsa hech narsa o'zgarmaydi):
  - `sanani_kochirish` (FT-17.1): to'lovlar saqlanadi; yangi sanada libos band bo'lsa eski bron joyida qoladi;
  - `libosni_almashtirish` (FT-17.2): narx farqi jamiga qo'shiladi/ayiriladi, chegirma saqlanadi; to'langan summa
    yangi jamidan oshsa rad etiladi;
  - `zakazni_bekor_qilish` (FT-17.3/17.4): standart qoida 30+ kun 100%, 7–29 kun 50%, <7 kun 0%; qaytariladigani kassadan
    «vozvrat», qolgani `ushlab_qolingan_avans` (boshqa daromad); libos darhol bo'shaydi; sabab majburiy; qoidadan
    tashqari foizni faqat rahbar beradi (Ilova B). C.4 / S10 testda.
  - «Berildi» dan keyin o'zgartirish/bekor yo'q (FT-17.6) — faqat muddatidan oldin qaytarish.
- `ZakazTarixi` jurnali (FT-17.5): kim, qachon, eski/yangi, sabab.
- API: `POST /api/zakazlar/<id>/sana-kochirish|libos-almashtirish|bekor/`, `GET .../tarix/`.
- Hali yo'q: qaytarish qoidasini admin paneldan sozlash va shartnomaga band qilib yozish (hozir kodda `STANDART_QOIDA`),
  rahbarga Telegram xabar (FT-17.5), P&L da «qaytarilmagan avans» qatori.

## Bajarildi (7-qism: P&L, xarajatlar, ro'yxatlar, frontend ekranlari)
- **finance** (TZ ziddiyati #1 hal qilindi: xarajat kiritish 1-bosqichga olindi):
  - `Xarajat` (modda: tozalash/tamir = to'g'ridan-to'g'ri, qolgani operatsion); sotuvchi xarajati kassadan chiqim va rahbar tasdig'ini
    kutadi, rahbarniki darhol tasdiqlangan (kassadan yoki kassasiz). Rad etilgan xarajatning kassa chiqimi qaytmaydi (pul jismonan chiqqan).
  - `reports.foyda_zarar` (6.2): Ilova C.1 / S14 aniq raqamlar bilan testda (sof foyda 30 720 000, 29,3%); tushum = shu oyda to'liq
    to'langan zakazlar (bekorlari chiqariladi); amortizatsiya = tannarx / muddat (sotilgan, tasdiqsiz, 24 oydan oshgan libos hisoblanmaydi);
    boshqa daromad = jarimalar + qaytarilmagan avans; soliq 4% × (tushum + boshqa daromad); tannarxsiz libos ogohlantirishi (FT-18.6).
  - `reports.kutilayotgan_daromad` (6.1, FT-19.6): Ilova C.5 / S22 testda.
  - API: `/api/xarajatlar/`, `/api/xarajatlar/<id>/qaror/`, `/api/hisobotlar/pnl/?oy=`, `/api/hisobotlar/kutilayotgan/?sana=` (hisobotlar faqat rahbar).
- **orders**: `GET /api/zakazlar/royxat/?holat=&q=`, `GET /api/zakazlar/<id>/` (karta), `GET /api/bosh-ekran/` (FT-1.2), `GET /api/dashbord/` (6.5).
- **Frontend** (pastki menyu): Dashbord (rahbar: bugun, tasdiq kutmoqda tugmalari, shu oy, ogohlantirish, P&L), Bosh, Yangi zakaz,
  Zakazlar (karta: avans/qoldiq, chegirma, berish+zalog, qaytarish, qarz, sana ko'chirish, bekor, tarix), Kassa (smena, hisobot,
  xarajat, chiqish, yopish).
- Brauzerda tekshirildi (login → PIN → Dashbord/Bosh/Kassa) va **topilgan xato tuzatildi**: CORS `X-Device-Token` ni ruxsat etmagan
  (xodimlar ro'yxati bloklanardi) — regressiya testi bor. Esda tut: yangi migratsiyadan keyin dev bazada `manage.py migrate`.
- Brauzerda to'liq oqim (zakaz yaratish → avans → berish → qaytarish) qo'lda sinalmagan; API darajasida testlar bor.

## Keyingi qadamlar (yangilangan)
1. Frontend: kassa/smena ekrani va avans qabul qilish.
2. Zalog (pul/hujjat/tillo, dalolatnoma), berish va qaytarish (4.9), jarima.
3. Chegirma so'rovi va tayyor chegirmalar (4.11), zakaz o'zgartirish/bekor qilish (4.17).
4. Oddiy P&L (6.2, Ilova C.1) — `tolangan_sana` asosida.

## Bajarildi (8-qism: katalog, 3-qism)
- **catalog**: `libos_qoshish` / `libosni_tasdiqlash` / `libosni_ozgartirish` (`services.py`):
  - sotuvchi libos qo'shadi, tannarx yuborsa ham e'tiborga olinmaydi, libos «Tasdiq kutilmoqda» va zakazda ko'rinmaydi (FT-3.5, 3.6, S07);
  - rahbar narx + tannarx kiritib tasdiqlaydi; rahbar qo'shgani darhol katalogda (S23 ning rahbar tomoni);
  - narx/tannarx/zalog o'zgarishi va libos qo'shilgani `Jurnal` ga yoziladi: kim, qachon, eski/yangi (FT-3.7, 3.8);
  - hayot oxiri holatlari: sotildi / hisobdan chiqarildi / arxiv / ta'mirda (FT-3.9; P&L ga sotuv/zarar yozish hali yo'q).
- `tenants.Jurnal` + `jurnalga_yoz` (umumiy jurnal); `GET /api/jurnal/` (rahbar).
- API: `GET|POST /api/liboslar/`, `GET|PATCH /api/liboslar/<id>/`, `POST .../tasdiq/`, `GET|POST /api/kategoriyalar/`.
  Tannarx va amortizatsiya sotuvchi javobida umuman yo'q.
- Frontend: «Katalog» bo'limi (qidiruv, libos qo'shish, rahbar uchun tasdiq kutayotganlar + narx/tannarx tahrirlash + holat, kategoriya qo'shish).
- Hali yo'q: rasm yuklash (7.3), «libos qo'shish huquqi» va «sotuvchi libosini tasdiqlash» sozlamalari (hozir qotirilgan: ikkalasi qo'shadi,
  tasdiq yoqilgan), aksessuarlar (4.4), ta'mir jurnali (FT-3.10), tasdiq kutayotgan libos haqida rahbarga Telegram xabar.

## Bajarildi (9-qism: rasm yuklash, 7.3)
- **catalog/rasm.py** (Pillow): yuklangan rasm tekshiriladi (JPEG/PNG/WebP, 10 MB gacha, 50 MP chegarasi, buzilgan/soxta fayl rad etiladi),
  EXIF burilishi qo'llanadi, shaffoflik oq fonga o'tadi, nisbat saqlanib 2:3 kadrga sig'diriladi (oq fon, markazda):
  - katta 800×1200 WebP ≤ 300 KB, kichik 300×450 WebP ≤ 50 KB (sifat pasaytirib moslanadi); asl nusxa alohida saqlanadi (S17);
  - standart bo'lmagan rasm (2:3 dan ±12% dan ko'p farq yoki 400×600 dan kichik) qabul qilinadi, lekin `standart=False` va rahbarga
    «N ta rasm standart emas» belgisi chiqadi;
  - bitta libosga 10 tagacha rasm; fayl nomlari uuid, `rasmlar/<salon_id>/` papkasida (taxmin qilib bo'lmaydi); o'chirilganda diskdan ham ketadi.
- API: `POST /api/liboslar/<id>/rasmlar/` (multipart, maydon «rasm»; har bir xodim, «faqat ko'rish» salonda yo'q),
  `DELETE /api/rasmlar/<id>/` (rahbar yoki yuklagan xodim); libos ro'yxati/kartasi/bo'sh liboslarda `rasm`, `rasmlar` havolalari (prefetch, N+1 yo'q).
- Frontend: `RasmBlok` (ko'p fayl tanlash, galereya, kattalashtirish, o'chirish, yo'riqnoma), katalog va «Yangi zakaz» ro'yxatlarida eskizlar.
  Brauzerda haqiqiy fayl yuklash bilan sinaldi.
- ESLATMA/xavf: hozir fayllar lokal `backend/media/` da va DEBUG da `/media/` orqali ochiq beriladi. Ishlab chiqarishda 7.1 bo'yicha
  O'zbekistondagi S3-mos saqlash + imzolangan/avtorizatsiyali havola kerak (uuid nomlar faqat vaqtinchalik himoya, FT-22.4/7.4).
  Fonni olib tashlash (raqamli manekin) 3-bosqichda; hujjat/tillo rasmlari va ularni 30 kundan keyin avtomatik o'chirish hali yo'q.

## Bajarildi (10-qism: aksessuarlar, 4.4)
- **Modellar**: `catalog.Aksessuar` (tur: nomi, kod, kategoriya, ijara narxi, tannarx, holat) va `AksessuarDona` (har bir jismoniy dona,
  yorliq `KOD-NN`, salonda noyob); `bookings.AksessuarBron` (dona + sana oralig'i, ExclusionConstraint); `orders.ZakazAksessuar`
  (zakazga qaysi dona berilgani va o'sha paytdagi narx, FT-4.2).
- **Bandlik**: `bosh_aksessuarlar` (kamida bitta bo'sh donasi borlari va soni), `aksessuar_bron_qilish` (yetarli dona bo'lmasa hech narsa
  band qilinmaydi); bufer kun kategoriyadan (standart 1); ta'mirdagi/yo'qolgan dona berilmaydi.
- **Zakaz**: `zakaz_yaratish(aksessuar_idlari=[...])` — takrorlangan id = soni; narx asosiy narxga qo'shiladi (FT-4.3); avans aksessuar bronini
  ham mustahkamlaydi; bekor qilinsa donalar bo'shaydi; sana ko'chirilganda aksessuarlar ham qayta band qilinadi (boshqa dona chiqishi mumkin).
- **Katalog**: sotuvchi qo'shgan aksessuar tannarxsiz va rahbar tasdig'ini kutadi (libos kabi); rahbar narx/tannarx, dona qo'shish,
  dona holati (ta'mirda/yo'qolgan/arxiv; kelgusi broni bor donani o'zgartirib bo'lmaydi), arxiv. O'zgarishlar jurnalga.
- API: `GET|POST /api/aksessuarlar/`, `GET|PATCH /api/aksessuarlar/<id>/`, `POST .../tasdiq/`, `POST .../donalar/`, `PATCH /api/donalar/<id>/`,
  `GET /api/bronlar/bosh-aksessuarlar/?dan=&gacha=`; `POST /api/zakazlar/` da `aksessuarlar` maydoni.
- Frontend: «Yangi zakaz»da aksessuar tanlash (+/− hisoblagich, bo'sh dona soni, jami narx), zakaz kartasida yorliqlar,
  Katalogda «Liboslar | Aksessuarlar» bo'limlari, kategoriya qo'shishda turi. `demo_ezaz` endi fata (3) va toj (2) ham yaratadi.
  Brauzerda to'liq sinaldi (zakaz: 1 libos + 2 fata = 2 700 000, kartada FT-01, FT-02). Topilgan kamchilik tuzatildi: «Zakazni saqlash»
  paneli pastki menyu ostida qolardi.
- QARORLAR (TZ da aniq emas): aksessuar uchun qulf (15 daqiqa) yo'q — bazadagi cheklov yetarli; sistema donani o'zi tanlaydi (eng kichik yorliq);
  aksessuar amortizatsiyasi P&L ga kirmaydi (TZ faqat «libos amortizatsiyasi» deydi); qaytarishda aksessuar alohida tekshirilmaydi
  (faqat umumiy «aksessuar yo'q» holati). Zakazdagi aksessuarni keyin qo'shish/olib tashlash hali yo'q.

## Bajarildi (11-qism: «Mijozga ko'rsatish» rejimi, FT-23.1)
- `POST /api/auth/pin-tekshir/` — kirgan xodim PIN ini qayta tasdiqlaydi; noto'g'ri PIN 400 (401 emas, sessiya tirik qoladi), 5 xato = 15 daqiqa blok
  (PIN login bilan umumiy `pin_tekshir`).
- Bo'sh liboslar javobida `rasm_katta` va `rasmlar` (barcha rakurslar, 800×1200).
- Frontend `Vitrina`: to'liq ekran, menyular yashirin; faqat katta rasm (bosib rakurs almashtiriladi), nomi, kategoriya/o'lcham, ijara narxi;
  «Oldingi/Keyingi»; tanlangan liboslar bo'lsa ular, aks holda sanadagi barcha bo'sh liboslar; chiqish faqat PIN bilan. Brauzerda sinaldi.
- Eslatma: brauzer «orqaga» tugmasi yoki sahifani yangilash rejimdan chiqaradi (sessiya saqlanadi) — to'liq kiosk himoyasi emas.

## Bajarildi (12-qism: ta'mir jurnali, FT-3.10)
- `catalog.TamirYozuvi` (ish turi, usta, boshlangan/tugagan sana, narx, xarajat bog'lanishi; libosda bir vaqtda bitta ochiq ta'mir — DB cheklovi).
- `catalog/tamir.py`: `tamirga_berish` — libos «Ta'mirda» (zakazda ko'rinmaydi, FT-2.3); mijozdagi, sotilgan libos berilmaydi;
  `tamirni_tugatish` — libos yana bo'sh, kunlar hisoblanadi (kamida 1), narx `tamir` moddasida xarajat bo'lib P&L ning
  «to'g'ridan-to'g'ri xarajat» qatoriga tushadi. Sotuvchi kiritgan narx kassadan chiqim + rahbar tasdig'i (smena kerak), rahbarniki darhol tasdiqlangan.
- «Ta'mirda» holatini endi qo'lda qo'yib bo'lmaydi — faqat jurnal orqali; ochiq ta'miri bor libos holatini qo'lda o'zgartirib bo'lmaydi.
- API: `GET|POST /api/liboslar/<id>/tamir/`, `POST /api/tamir/<id>/tugatish/`. Frontend: libos kartasida «Ta'mir jurnali» bloki. Brauzerda sinaldi.
- Eslatma: ta'mirga berilgan libosning kelgusi bronlari saqlanadi (ulgurish rahbar zimmasida) — ogohlantirish hali yo'q.
  Aksessuar donalari uchun ta'mir jurnali yo'q (faqat holat). Moslash xizmatini zakazga narx bilan qo'shish (FT-2.8) hali yo'q.

## Bajarildi (13-qism: admin panel sozlamalari, xodimlar, hujjatlar, real-time)
- **Sozlamalar (4.16, 1-bosqichdagi 6 ta)**: `tenants.SalonSozlamalari` + `sozlama(salon)`; `GET|PATCH /api/sozlamalar/` (o'qish — hamma, yozish — rahbar,
  har bir o'zgarish jurnalga). Endi kodda qotirilgan emas, sozlamadan olinadi:
  bufer kun (libos > kategoriya > sozlama), vaqtinchalik bron soati, zalog turlari (o'chirilgani `libos_berish` da rad etiladi),
  kechikish jarimasi (yoqilsa qaytarishda avtomatik, S09), avans qaytarish qoidasi (tekshiruv: kunlar kamayadi, 0 bilan tugaydi, foiz oshmaydi),
  sotuvchi libosi/aksessuarini tasdiqlash (o'chirilsa darhol katalogda, S23).
- **Xodimlar (FT-22.3)**: `GET|POST /api/xodimlar-boshqaruv/`, `PATCH .../<id>/` — qo'shish, rol, faol/nofaol, PIN tiklash (blokni ham ochadi; PIN jurnalga
  tushmaydi), 4–6 raqam; oxirgi faol rahbarni o'chirib/pasaytirib bo'lmaydi; nofaol xodimning ochiq sessiyasi darhol yopiladi.
- **Salon rekvizitlari (FT-22.6)**: `GET|PATCH /api/salon/` (nomi, yuridik nom, STIR, manzil, telefon, rang).
- **Hujjatlar (FT-10.2, 10.3, 16.1, 7.4)**: `GET /api/zakazlar/<id>/hujjat/?tur=shartnoma|kvitansiya|dalolatnoma` (`orders/hujjatlar.py`).
  Shartnoma bandlari sozlamaga qarab yig'iladi: jarima bandi faqat yoqilgan bo'lsa; zalog bandi olingan zalog turiga (yoki yoqilgan turlarga) mos;
  qaytarish qoidasi va shaxsiy ma'lumotga rozilik har doim. Chegirma tasdiq kutayotganda shartnoma/kvitansiya chop etilmaydi (FT-11.3).
  Frontend `Hujjat`: chop etish ko'rinishi, «Chop etish / PDF» brauzer oynasi orqali (alohida PDF generator yo'q — qaror).
- **Real-time (FT-1.4)**: «Yangi zakaz»dagi bo'sh liboslar/aksessuarlar har 4 soniyada yangilanadi; band bo'lib qolgan tanlov chiqariladi.
- Frontend: rahbar uchun «Sozlama» bo'limi (sozlamalar, rekvizitlar, xodimlar); zalog formasi faqat yoqilgan turlarni ko'rsatadi; bekor formasi
  amaldagi qoidani ko'rsatadi; summalar hamma joyda `2 400 000 so'm` formatida.
- Brauzerda topilib tuzatildi: dalolatnomadagi `qaytarish` kaliti asosiy `qaytarish` sanasini bosib, shartnoma sahifasi yiqilardi
  (endi `qaytarish_akti`); test topgan: tillo o'chirilganda ham zalog bandida «tillo buyum» chiqardi.
- Hali yo'q: 4.16 ning qolgan sozlamalari (2–3-bosqich), shartnoma shablonini tahrirlash, ishonchli qurilmalar ro'yxati, rahbar uchun Telegram kod,
  avtomatik chiqish (10 daqiqa, FT-1.6) va «Xodimni almashtirish» tugmasi (FT-1.5), kvitansiya/dalolatnomani brauzerda ko'rib sinash.

## Bajarildi (14-qism: kalendar, avtomatik chiqish, xodimni almashtirish)
- **Bandlik kalendari (FT-2.6)**: `GET /api/bronlar/kalendar/?dan=&gacha=` (3 oygacha) — libos bo'yicha bronlar: zakaz sanalari, bufer bilan band
  oxirgi kun, turi, zakaz raqami, mijoz. Frontend «Kalendar» bo'limi (rahbar va sotuvchi): kun / hafta / oy, sana bo'yicha o'tish,
  bron / vaqtinchalik bron / tozalash (bufer) ranglari, katakni bosganda zakaz kartasi; har 5 soniyada yangilanadi. Brauzerda sinaldi.
- **Avtomatik chiqish (FT-1.6)**: 10 daqiqa harakatsizlikdan keyin xodim PIN ekraniga qaytadi, salon logini qurilmada qoladi (muddat hozir kodda
  `HARAKATSIZLIK_MS`, admin sozlamasi 2-bosqichda). Brauzerda 10 daqiqa kutib sinalmagan.
- **Xodimni almashtirish (FT-1.5)**: yuqoridagi tugma PIN ekraniga qaytaradi (avvalgi «Chiqish»).

## Bajarildi (15-qism: platforma paneli, obuna, oyni yopish, oflayn rejim)
- **Platforma egasi (4.19)**: `PlatformaAdmini`, `Tarif`; alohida token (`PlatformTokenAuthentication`, boshqa tuz) — xodim tokeni platforma
  API siga, platforma tokeni esa salon ma'lumotiga yaramaydi (testda 7 ta salon endpointi tekshirilgan, FT-22.5).
  `POST /api/platforma/login/` (5 xato = 15 daqiqa blok), `GET|POST /api/platforma/salonlar/`, `PATCH .../<id>/` (bloklash, tarif, parol tiklash,
  sinovni uzaytirish), `POST .../<id>/tolov/` (obunani qo'lda N oyga uzaytirish, FT-22.9), `GET|POST /api/platforma/tariflar/`.
  Yangi salon shablon bilan: rahbar + PIN, 3 libos va 5 aksessuar kategoriyasi, standart sozlamalar, 14 kunlik sinov (FT-22.1, 22.7).
  Egasi ro'yxatda faqat umumiy faollikni ko'radi: zakazlar soni, faol xodimlar, oxirgi kirish, obuna holati.
  Akkaunt yaratish: `python manage.py platforma_admin <login>` (parol so'raladi, kamida 10 belgi). Panel: `http://localhost:5173/#platforma`.
- **Obuna (FT-22.8, S29)**: `Salon.obuna_holati()` — sinov -> faol -> muddat o'tgach 7 kun ogohlantirish -> «faqat ko'rish» (ma'lumot saqlanadi,
  yozish 403). Holat har so'rovda sanalarga moslanadi; rahbarga banner. Tarif bo'yicha xodimlar limiti. Sanasi yo'q salon (demo) cheklanmaydi.
- **Oyni yopish (FT-18.4, 18.6, S13)**: `finance.YopilganOy` (yopish paytidagi P&L saqlanadi); tugamagan oy, tannarxsiz libos yoki
  tasdiqlanmagan xarajat bo'lsa yopilmaydi; yopilgan oyga xarajatni faqat rahbar kiritadi; qayta ochish mumkin.
  `GET|POST|DELETE /api/hisobotlar/oyni-yopish/`; dashbordda tugma.
- **Zakazga aksessuar qo'shish/olib tashlash**: `POST /api/zakazlar/<id>/aksessuar/`, `DELETE .../aksessuar/<qator_id>/`; narx va bandlik qayta
  hisoblanadi, tarixga yoziladi; to'langan summa yangi jamidan oshsa olib tashlab bo'lmaydi. Zakaz kartasida blok.
- **Oflayn «faqat ko'rish» (7-bo'lim, S28)**: `GET /api/oflayn-toplam/` — bugungi/ertangi bronlar, telefonlar, saqlanayotgan zaloglar (narx, to'lov,
  hujjat raqami kirmaydi); qurilmada har 5 daqiqada keshlanadi. Javob kelmasa ilova «Internet yo'q: faqat ko'rish rejimi»ga o'tadi, menyu
  yashiriladi, har 10 soniyada aloqani tekshiradi va o'zi qaytadi. Tarmoq xatosida sessiya va qurilma tokeni endi o'chmaydi.
  Brauzerda serverni o'chirib-yoqib sinaldi (oflaynda sahifani yangilash ham).
- Hali yo'q: «yordam ruxsati» (egasiga vaqtinchalik ko'rish huquqi, FT-22.5), salonni platformadan chiqarish/arxiv (FT-22.10), filiallar,
  ishonchli qurilmalarni boshqarish, obuna to'lovini Click/Payme orqali (FT-22.9), sozlash ustasi (FT-22.7 ikkinchi qismi).
  Platformada salon qo'shish, to'lov va bloklash tugmalari brauzerda bosib sinalmagan (API testlari bor).

## Bajarildi (16-qism: ishonchli qurilmalar, yordam ruxsati, boshlash ro'yxati)
- **Ishonchli qurilmalar (FT-22.2)**: salonning birinchi qurilmasi darhol ishonchli; keyingilari rahbar ruxsatini kutadi
  (`IshonchliQurilma.tasdiqlangan`). Kutayotgan qurilma xodimlar ro'yxatini ham ko'ra olmaydi (403 `qurilma_kutilmoqda`), ekranda kutadi va
  ruxsat berilgach o'zi ochiladi (5 soniyalik tekshiruv). `GET /api/qurilmalar/`, `PATCH .../<id>/ {tasdiq}`, `DELETE .../<id>/`.
  Xodim tokeniga qurilma bog'langan: qurilma chiqarilsa undagi ochiq sessiyalar darhol yopiladi. Oxirgi ishonchli qurilmani o'chirib bo'lmaydi;
  rahbar yagona qurilmasini yo'qotsa, platforma egasi «qurilmalarni tozalaydi» (`PATCH /api/platforma/salonlar/<id>/ {qurilmalarni_tozala}`).
  Qurilma nomi brauzer/tizim/vaqtdan avtomatik («Chrome · Windows · 09.10 12:50»).
- **Salon paroli**: rahbar o'zgartiradi (`POST /api/salon/parol/`); salon logini endi 5 xato paroldan keyin 15 daqiqaga bloklanadi
  (avval cheklov yo'q edi).
- **Yordam ruxsati (FT-22.5)**: rahbar 1–72 soatga beradi/bekor qiladi (`GET|POST|DELETE /api/yordam-ruxsati/`); platforma egasi
  `GET /api/platforma/salonlar/<id>/yordam/` orqali faqat o'qiydi (oxirgi 50 zakaz + shu oy P&L); ruxsatsiz 403; har bir kirish salon jurnaliga yoziladi.
- **Boshlash ro'yxati (FT-22.7, soddalashtirilgan sozlash ustasi)**: `GET|POST /api/boshlash/` — rekvizit, xodimlar, kategoriyalar, birinchi liboslar;
  dashbordda bosiladigan qadamlar, hammasi bajarilsa yoki yashirilsa ko'rinmaydi. To'liq ko'p qadamli usta emas — qaror.
- Frontend: kirishda «ruxsat kutilmoqda» ekrani; «Sozlama»da Qurilmalar, salon paroli, Texnik yordam ruxsati; platformada qurilmalarni tozalash
  va yordam ko'rinishi. Brauzerda sinaldi: yangi qurilma kutadi -> ruxsatdan keyin o'zi ochiladi; boshlash ro'yxati; sozlamadagi bloklar.
- Hali yo'q: rahbar uchun Telegram kod (2-bosqich), filiallar, salonni platformadan chiqarish (FT-22.10).

## Bajarildi (17-qism: mijozlar, ekran 14)
- `Mijoz` ga o'lchamlar (ko'krak, bel, son, bo'y, oyoq kiyim; FT-8.4) va izoh qo'shildi.
- `GET /api/mijozlar/?q=&qora_royxat=1` — to'liq ro'yxat faqat rahbarga; sotuvchi kamida 4 ta belgi bilan qidiradi (bazani varaqlay olmaydi, 7.4).
  `GET|PATCH /api/mijozlar/<id>/` — karta, zakazlar tarixi, tahrirlash (F.I.O., qo'shimcha telefon, to'y sanasi, manba, o'lchamlar; sotuvchi ham).
  `POST /api/mijozlar/<id>/qora-royxat/` — faqat rahbar, sabab majburiy, jurnalga yoziladi (FT-8.3).
- Frontend: «Mijozlar» bo'limi (qidiruv, karta, o'lchamlar, qora ro'yxat, tarixdan zakazga o'tish); «Yangi zakaz»da yangi mijoz uchun F.I.O. maydoni
  va mavjud mijozning o'lchamlari ko'rsatiladi. Brauzerda ro'yxat va karta ochib ko'rildi.
- Hali yo'q: o'lchamni libos tanlash filtriga avtomatik qo'yish (FT-8.4 ikkinchi qismi; liboslarda o'lcham filtri umuman yo'q — FT-3.2),
  «Qarzdorlar» va «Qoldiq kutilmoqda» ro'yxatlari (FT-12.13), salonchilar (2-bosqich).

## Bajarildi (18-qism: filtrlar, avtomatik bekor, eslatmalar, qarzdorlar)
- **Libos filtrlari (FT-3.2) va qidiruv (FT-2.2)**: «Yangi zakaz»da kategoriya tugmalari, o'lcham, rang, «narx gacha» (brauzerda filtrlanadi)
  va artikul/nom bo'yicha qidiruv (`GET /api/bronlar/bosh/?q=` — band libos ham chiqadi). Band libosda `eng_yaqin_bosh` — shu davomiylikdagi
  eng yaqin bo'sh sana (ketma-ket bronlar va bufer hisobga olinadi, S27).
- **Vaqtinchalik bronni avtomatik bekor qilish (FT-2.5, S04)**: `orders.changes.muddati_otganlarni_bekor_qil` — avans kiritilmagan, bron muddati
  o'tgan zakaz «Bekor qilingan» bo'ladi (sabab yoziladi), libos va aksessuar bo'shaydi, kutayotgan chegirma so'rovi yopiladi, tarixga
  `avtomatik_bekor` tushadi. Pul olingan zakaz hech qachon o'zi bekor bo'lmaydi. Ishga tushadi: bosh ekran va zakazlar ro'yxati ochilganda
  hamda `python manage.py bronlarni_tozalash` (serverda cron uchun). AVVAL: bunday zakaz abadiy «vaqtinchalik» bo'lib qolardi.
- **Eslatmalar (4.14, FT-14.1, 14.2, S15)**: bosh ekranda — ertaga olib ketadi, bugun qaytarishi kerak, N kun kechikdi, bron tugashiga 2 soat
  qoldi. «Bog'landim» (`POST /api/zakazlar/<id>/boglandim/`) natijani zakaz tarixiga yozadi; o'sha kuni eslatma bajarilgan deb ko'rinadi.
  Telegram orqali yuborish — 2-bosqich.
- **Qarzdorlar (FT-12.13)**: `GET /api/hisobotlar/qarzdorlar/` (rahbar) — «Qarzdorlar» (qaytarishdan keyingi jarima qarzi) va «Qoldiq kutilmoqda»
  (avans olingan, libos berilmagan; qarz emas) alohida; dashbordda blok.
- Brauzerda sinaldi: eslatma + «Bog'landim», filtrlar, band libosda eng yaqin bo'sh sana.
- Hali yo'q: mijoz o'lchamini filtrga avtomatik qo'yish (FT-8.4), band libos uchun «o'xshash bo'sh liboslar» taklifi (FT-2.2).

## Bajarildi (19-qism: Telegram xabarlari — 2-bosqich boshlandi; kichik bo'shliqlar)
- **Kichik bo'shliqlar**: `Mijoz.kiyim_olchami` — libos tanlashda o'lcham filtriga o'zi qo'yiladi (FT-8.4); band libos yonida shu kategoriyadagi
  (avval shu o'lchamdagi) 3 tagacha bo'sh libos taklif qilinadi (`oxshashlar`, FT-2.2).
- **`apps/notify`** (7.2, 4.14):
  - `Xabar` navbati/jurnali (kutilmoqda / yuborildi / xato / ulanmagan), `TelegramUlash` (bir martalik kod), `KirishKodi`; `Xodim.telegram_id`.
  - `telegram.py` — Bot API ga oddiy HTTPS so'rov (tashqi kutubxonasiz). **TZ dan chetlanish:** 7.1 da aiogram tavsiya etilgan; hozirgi hajm uchun
    to'g'ridan-to'g'ri API yetarli va test qilish oson — kerak bo'lsa `telegram_bot` buyrug'i aiogram ga ko'chiriladi.
  - Xabar yuborishdagi xato asosiy amalni buzmaydi (tranzaksiya tugagach yuboriladi; xato `Xabar.xato_matni` ga yoziladi; token matnga chiqmaydi).
  - Hodisalar: chegirma so'rovi -> rahbarga «Tasdiqlash / Rad etish» tugmalari (FT-11.2); kassa farqi (FT-12.10); sotuvchi qo'shgan libos (FT-3.6);
    zakaz ko'chirildi/almashtirildi/bekor qilindi (FT-17.5); PIN 5 marta xato (FT-1.7).
  - Tugmani faqat shu akkauntga bog'langan rahbar, faqat o'z saloni so'rovi uchun bosa oladi.
  - Rahbar kirishi (FT-1.1, FT-22.3): rahbar Telegram ulagan VA bot sozlangan bo'lsa, PIN dan keyin 6 raqamli kod so'raladi (5 daqiqa, 5 urinish,
    bir martalik). Aks holda faqat PIN — bot ishlamay qolsa rahbar qulflanib qolmaydi (kod yuborilmasa 503).
  - API: `GET|POST|DELETE /api/telegram/` (holat, ulash kodi, uzish), `GET /api/xabarlar/` (rahbar: nima yuborildi, nima yetmadi).
  - Buyruqlar: `telegram_bot` (long polling: `/start <kod>`, tugmalar; faqat shaxsiy chatda), `eslatmalarni_yuborish` (cron: har soatda; har eslatma
    kuniga bir marta), `kunlik_hisobot` (cron: 21:00; FT-15.5).
- Frontend: bosh ekranda «Telegram xabarlari» bloki (kod, `/start`, o'zi yangilanadi); kirishda Telegram kod qadami.
- SINALMAGAN: haqiqiy Telegram bilan (token yo'q). Testlarda Bot API soxtalashtirilgan; brauzerda ulash oqimi `/start` ni serverda taqlid qilib sinaldi.
- Ishga tushirish: `.env` ga `TELEGRAM_BOT_TOKEN` (BotFather) va `TELEGRAM_BOT_NAME`; alohida jarayon: `python manage.py telegram_bot`.
- Hali yo'q: SMS (Eskiz), eslatma vaqtini/kunlik hisobot vaqtini admin paneldan sozlash, mijozga xabar (TZ bo'yicha kerak emas).

## Bajarildi (20-qism: salonchilar va hisobotlar — 2-bosqich)
- **Salonchilar (4.6)**: `orders.Salonchi` (ism, telefon, Instagram, salon, manzil), `Zakaz.salonchi`. `GET|POST /api/salonchilar/`,
  `PATCH .../<id>/`, `POST /api/zakazlar/<id>/salonchi/`. Sotuvchi zakaz ichidan tezda qo'shadi (FT-6.3); Instagram maydoni faqat
  instagram.com havolasiga keltiriladi (begona/`javascript:` havola rad etiladi); statistika (mijozlar soni, to'liq to'langan tushum)
  faqat rahbarga (FT-6.4); komissiya yo'q (FT-6.5). Salonchi tanlansa yangi mijoz manbasi «salonchi», aks holda sotuvchi tanlaydi (FT-8.2).
- **Hisobotlar (6.3, 6.6)**: `finance/statistika.py` — 16 ta hisobot bitta ko'rinishda (`ustunlar`, `qatorlar`, `jami`):
  libos samaradorligi, kategoriyalar, sotuvchilar, salonchilar, mijoz manbalari, zaloglar reestri, zalog statistikasi, qoplamagan va bo'sh
  liboslar (FT-15.3), bekor qilingan zakazlar, kechikish va jarimalar, xarajatlar, pul oqimi, kunlik kassa, bandlik (%), kelgusi bronlar
  (FT-18.5), chegirmalar. `GET /api/hisobotlar/royxat/`, `GET /api/hisobotlar/h/<nom>/?dan=&gacha=` (faqat rahbar; 1 yilgacha).
  Bitta to'liq ssenariy (2 zakaz aylanadi, 1 bekor, chegirma, xarajat, kechikish) bo'yicha raqamlar testda tekshirilgan.
- Frontend: rahbar uchun «Hisobot» bo'limi (tanlov + davr + jadval; fayl yuklab olish yo'q — FT-18.3); «Mijozlar» ichida «Salonchilar»;
  «Yangi zakaz»da salonchi tanlash, Instagramni ochish, tezda qo'shish, mijoz manbasi; zakaz kartasida salonchi.
- Tuzatildi: bazadan o'qilgan chegirma foizi «10.00%» bo'lib chiqardi (hisobot va Telegram xabarida) — endi «10%».
- Hali yo'q: hisobotlarda kategoriya/sotuvchi filtri (FT-20.1) va «o'tgan oy / o'tgan yil bilan taqqoslash» (FT-18.1), qatorni bosib tafsilotga
  o'tish (FT-18.2), grafiklar (12 oylik tushum), salonchi promokodlari (3-bosqich), bank ko'chirmasi bilan solishtirish (FT-12.12).
- Brauzerda: «Hisobot» sahifasi ochib ko'rildi; salonchi tanlash va Salonchilar ro'yxati brauzerda sinalmagan (API testlari bor).

## Bajarildi (21-qism: hisobot filtrlari, taqqoslash, 12 oylik grafik, bank solishtiruvi)
- **Filtrlar (FT-20.1)**: `GET /api/hisobotlar/h/<nom>/?kategoriya=&sotuvchi=` — har hisobotda faqat ma'noli filtr ishlaydi (`statistika.FILTRLAR`):
  kategoriya — libos, bo'sh liboslar, bandlik; sotuvchi — kategoriya, salonchi, manba, bekor, kechikish, chegirma. Javobda `filtrlar` ro'yxati,
  frontend shunga qarab tanlovlarni ko'rsatadi. Tegishli bo'lmagan filtr e'tiborga olinmaydi.
- **Taqqoslash (FT-18.1)**: `GET /api/hisobotlar/pnl/` javobida `taqqos` — o'tgan oy va o'tgan yilning shu oyi (tushum, sof foyda, zakazlar);
  P&L ostida foiz o'zgarishi bilan ko'rsatiladi.
- **12 oylik grafik (6.5)**: `GET /api/hisobotlar/oylik/`; `OylikGrafik` (SVG): tushum va sof foyda ikki alohida grafikda (ikki o'qli emas),
  ustiga olib borganda aniq qiymat, faqat eng katta va oxirgi oy yozilgan. Rang (#9a4c95) palitra validatoridan o'tkazilgan
  (brend rangi #8b5e83 grafik uchun juda xira chiqib, tekshiruvdan o'tmagan edi). Brauzerda sinov ma'lumoti bilan ko'rildi.
- **Bank solishtiruvi (FT-12.12)**: `finance.BankSolishtirish`; `GET|POST /api/hisobotlar/bank/` — karta/Click/Payme bo'yicha tizimdagi tushum,
  ko'chirmadagi summa, komissiya va farq = ko'chirma − (tizim − komissiya). Komissiya «bank komissiyasi» xarajati bo'ladi (qayta kiritilsa
  yangilanadi, ikkilanmaydi). Frontend: «Hisobot» sahifasi pastida blok.
- Hali yo'q: hisobot qatorini bosib tafsilotga o'tish (FT-18.2), chorak/yil tugmalari (hozir ixtiyoriy sana oralig'i), grafikning jadval ko'rinishi
  (aniq raqamlar P&L va «Kategoriyalar» hisobotida). Bank bloki va filtr tanlovlari brauzerda bosib sinalmagan (API testlari bor).

## Bajarildi (22-qism: promokodlar, 4.18)
- **Model**: `orders.Promokod`, `PromokodIshlatilishi`; `Zakaz.promokod` / `promokod_chegirma`; sozlamalarda `promokod_tasdiqsiz`,
  `promokod_chegirma_birga`, `salonchi_kodlari`. Migratsiyalar: `tenants/0008`, `orders/0010` (dev bazaga qo'llangan).
- **Servis** (`orders/promo.py`): bir/ko'p martalik kod, foiz/summa/bepul aksessuar, muddat (1/3/6 oy yoki sana), limit, bitta mijozga,
  minimal summa, maksimal chegirma, kategoriya va hafta kuni shartlari, salonchi kodi, bir yo'la 500 tagacha noyob kod, to'xtatish/yoqish/
  arxiv/muddat uzaytirish, statistika (FT-21.11). Zakaz bekor bo'lsa yoki kod olib tashlansa — kod qayta bo'shaydi (FT-21.9).
- **API**: rahbar `GET|POST /api/promokodlar/`, `PATCH /api/promokodlar/<id>/`; sotuvchi `POST|DELETE /api/zakazlar/<id>/promokod/`.
- **Frontend**: zakaz kartasida «Promokod» bloki, «Mijozlar» → «Promokodlar» (rahbar), sozlamalarda uchta tugma.
- **Test**: `apps/orders/test_promo.py` — 35 ta (Ilova C.3, S19–S21) o'tdi. Lint va build toza.
- To'liq test: 398 ta, hammasi o'tdi.
- Brauzerda sinaldi: kod yaratish, noto'g'ri kod («Kod topilmadi»), to'g'ri kod (15%, maks 300 000 → 2 310 000 dan 2 010 000). Sinov ma'lumotlari tozalangan.
- Qarorlar: promokod faqat avans olinmagan zakazga; chegirma ustama qo'shilgan summadan; tasdiq kerak bo'lsa `ChegirmaSorovi` orqali.

## Bajarildi (23-qism: mavsumiy narx va sotuvchi bonusi, FT-15.1, FT-15.2)
- **Mavsumiy narx**: `orders.MavsumiyNarx` (sanalar oralig'i va/yoki hafta kunlari, foiz, faol); sozlama `mavsumiy_narx` (standart: o'chirilgan).
  Ustama olib ketish kuniga qarab avtomatik (`pricing.mavsumiy_foiz`); bir kunga bir nechta qoida to'g'ri kelsa **eng kattasi** olinadi
  (qo'shilmaydi — o'z qarorim). Sana ko'chirilsa ustama qayta hisoblanadi (FT-17.1); narx oshib qoldiq chiqsa `tolangan_sana` tozalanadi.
  API: rahbar `GET|POST /api/mavsumiy-narxlar/`, `PATCH|DELETE .../<id>/`; har bir xodim `GET /api/narx/ustama/?sana=`.
  Frontend: sozlamalarda qoidalar bloki; yangi zakaz ekranida «+ ustama 10% (210 000 so'm)»; zakaz kartasida «Mavsumiy ustama (10%)».
- **Sotuvchi bonusi**: sozlamalar `sotuvchi_bonusi`, `bonus_foiz` (standart: o'chirilgan). `reports.sotuvchi_bonuslari` — shu oyda to'liq
  to'langan zakazlar tushumidan foiz, faqat sotuvchi rolidagi xodimlarga. `GET /api/hisobotlar/bonus/?oy=`. Bonus P&L da operatsion
  xarajatga **avtomatik** qo'shiladi (`sotuvchi_bonusi` maydoni) — xarajat sifatida qo'lda qayta kiritilmasligi kerak.
  Frontend: «Hisobot» sahifasida «Sotuvchi bonusi» jadvali.
- Test: `orders/test_narx.py` (19 ta). Brauzerda sinaldi (qoida qo'shish, shanba kuniga ustama, bonus jadvali).

## Bajarildi (24-qism: primerka va mijoz bahosi, FT-2.8, FT-9.5, FT-15.4)
- **Primerka**: sozlama `primerka` (standart: o'chirilgan); `orders.Primerka` (vaqt, natija, moslash narxi, holat); `Zakaz.xizmatlar` —
  moslash xizmati summasi, asosiy narx ichida (FT-4.3), shuning uchun mavsumiy ustama unga ham qo'llanadi.
  `POST /api/zakazlar/<id>/primerka/`, `PATCH /api/primerkalar/<id>/`. Primerka faqat libos berilmagan zakazga, bugundan olib ketish
  kunigacha. Sotuvchi eslatmalarida (bugun/ertaga) va kalendarda («P 14:30» belgisi) ko'rinadi.
- **Mijoz bahosi**: sozlama `mijoz_bahosi` (standart: yoqilgan); o'chirilsa baho yozilmaydi va forma maydoni yashiriladi.
  «Libos samaradorligi» hisobotiga «O'rtacha baho» ustuni qo'shildi (sotuvchi bo'yicha avvaldan bor edi).
- Hali yo'q: primerkada mijoz o'lchamlarini shu oynadan yangilash (FT-8.4; mijoz kartasidan yangilanadi).
- Test: `orders/test_primerka.py` (16 ta). Brauzerda sinaldi (belgilash, moslash 150 000 → jami qayta hisoblandi, kalendar).

## Bajarildi (25-qism: P&L qatoridan tafsilot, FT-18.2)
- `GET /api/hisobotlar/pnl/tafsilot/?oy=&qator=tushum|togridan|amortizatsiya|operatsion|boshqa` — qatorni tashkil qilgan zakazlar,
  xarajatlar, liboslar (amortizatsiya), jarima va qaytarilmagan avanslar. Jami P&L dagi qatorga teng (test bilan tekshirilgan).
- Frontend: dashborddagi P&L da hisoblanmaydigan qatorlar bosiladigan; ostida ro'yxat ochiladi.
- Hali yo'q: 16 ta statistik hisobot qatoridan tafsilotga o'tish (faqat P&L uchun qilindi).
- «Hisobot» sahifasiga tayyor davr tugmalari qo'shildi: shu oy, o'tgan oy, shu chorak, shu yil (FT-18.1).
- Yo'l-yo'lakay tuzatildi: kalendarda sanani klaviaturadan terganda so'rov xato berardi (yil oraliq qiymatlari); 12 oylik grafikda
  manfiy ustun qiymati oy nomi ustiga tushardi.

## Bajarildi (26-qism: 4.16 ning qolgan sozlamalari)
- Yangi sozlamalar: `qulf_daqiqa` (15), `amortizatsiya_oy` (24 — yangi libos uchun standart), `sotuvchi_libos_qoshadi` (ha),
  `qoplamagan_royxat` + `qoplamagan_kun` (ha, 60), `kunlik_hisobot` + `kunlik_hisobot_vaqti` (ha, 21:00), `promokodlar_bolimi` (ha).
- Qoplamagan liboslar endi rahbar dashbordida ham chiqadi (FT-15.3); o'chirilsa hisobotlar ro'yxatidan ham yashiriladi.
- **Cron o'zgardi**: `kunlik_hisobot` buyrug'ini har 15 daqiqada ishga tushirish kerak — har salonga o'zi belgilagan vaqtdan keyin,
  kuniga bir marta yuboriladi.
- Hali yo'q: shartnoma shablonini tahrirlash, «Manekin» sozlamasi (manekin moduli yo'q).
- Test: `tenants/test_sozlamalar2.py` (8 ta), `notify` kunlik hisobot testlari yangilandi.

## Bajarildi (27-qism: salon platformadan chiqishi, FT-22.10)
- `Salon.chiqish_sanasi`, `chiqish_izohi`. Platforma egasi: `POST /api/platforma/salonlar/<id>/chiqish/` (asos majburiy — rahbarning
  yozma so'rovi) → salon bloklanadi, 90 kunlik sanoq boshlanadi; `DELETE` — bekor qilish; `GET .../arxiv/` — barcha ma'lumot JSON fayl.
  Arxiv **faqat chiqqan salon** uchun beriladi (FT-22.5 buzilmasligi uchun); parol/PIN xeshlari va kirish kodlari arxivga kirmaydi.
- `tenants/arxiv.py`: `salonni_ochirish` — 90 kun o'tgach salonni barcha jadvallari va fayllari bilan o'chiradi (boshqa salonga tegmaydi —
  test bilan tekshirilgan). **Avtomatik ishlamaydi**: `manage.py chiqqan_salonlar` (ro'yxat), `--arxiv <login> <fayl>`, `--ochirish`.
  O'chirishni cron'ga qo'yish yoki qo'lda ishlatish — platforma egasining qarori.
- Frontend: platforma panelida «Salon platformadan chiqdi», «Arxivni yuklab olish», «Chiqishni bekor qilish».
- Hali yo'q: rasmlar fayllarini arxivga qo'shish (media/ papkasidan alohida beriladi). Platforma paneli brauzerda bosib sinalmagan
  (dev bazada platforma admini yo'q); API va servis testlari bor (`tenants/test_arxiv.py`, 11 ta).

## Bajarildi (28-qism: rahbar dashbordi, FT-19.1–19.3, FT-19.5)
- `GET /api/dashbord/?davr=bugun|hafta|oy` (FT-19.2): «Shu oy» bloki tanlangan davrga moslashadi. Bugun/hafta uchun daromad (to'liq
  to'langan zakazlar), tasdiqlangan xarajatlar, zakazlar soni va o'rtacha chek; sof foyda faqat oy bo'yicha (amortizatsiya va soliq oylik).
  Kutilayotgan daromad davrga bog'liq emas — bugungi holat.
- Yangi blok «Oldinda: 30 kun»: liboslar yuklanganligi (%), avanslar portfeli, eng band 3 kun.
- Ogohlantirishlarga qo'shildi: oxirgi yopilgan smenadagi kassa farqi, 7 kun ichida tugaydigan promokodlar (bo'lim o'chirilgan bo'lsa chiqmaydi).
- Frontend: davr tugmalari, dashbord har 1 daqiqada o'zi yangilanadi (FT-19.1), ogohlantirish bosilganda tegishli bo'lim ochiladi (FT-19.3 —
  qisman: faqat ogohlantirishlar va kalendar havolasi; boshqa ko'rsatkichlar hali bosilmaydi).
- Test: `orders/test_royxat.py` → `DashbordDavrTests` (6 ta yangi). Brauzerda davr almashtirish ko'rildi.

## Bajarildi (29-qism: raqamli 2D manekin, 4.5 — birinchi versiya)
- **Fonsiz qatlam** (`catalog/manekin.py`): rasm foni serverning o'zida olib tashlanadi (tashqi xizmatga hech narsa yuborilmaydi, 7.3):
  chetdagi median rang «fon», chetga tutashgan o'xshash rangli maydon shaffof bo'ladi; libos ichidagi och joylar saqlanadi. Natija 800×1200
  shaffof WebP (≤400 KB), libos kesilib kanvas markaziga qo'yiladi. `POST /api/rasmlar/<id>/fonsiz/`.
- **Joylashuv** (FT-5.3): `Libos.manekin_rasm`, `manekin_x/y`, `manekin_kattalik`; `GET|PATCH /api/liboslar/<id>/manekin/`.
  Saqlangan holat libos kartasida va yangi zakaz ekranidagi bo'sh liboslar ro'yxatida qaytadi (S16).
- **Frontend** (`components/Manekin.jsx`): bitta standart manekin (SVG, FT-5.1), libos qatlami ustida; barmoq/sichqoncha bilan surish,
  ikki barmoq/g'ildirak/slayder bilan kattalashtirish, «Joylashuvni saqlash», «Rasmni saqlash / yuborish» (PNG; qurilmada «ulashish»
  bo'lsa Telegramga shu yerdan). Katalogda har rasm ostida «Manekinga»; yangi zakazda «Manekinda» tugmasi. Sozlama `manekin` (yoqilgan).
- **Hali yo'q / tekshirilmagan**:
  - Aksessuarlarni (fata, toj) qatlam qilib qo'shish (FT-5.2 ning ikkinchi qismi) — aksessuarlarda rasm yo'q.
  - Mijozga bot orqali to'g'ridan-to'g'ri yuborish (FT-5.4) — hozir rasm yuklab olinadi yoki qurilmaning «ulashish» oynasi ochiladi.
  - **Sifat mezoni FT-5.6 bajarilmagan**: algoritm faqat sun'iy rasmlar bilan sinalgan. Salonning 10 ta haqiqiy rasmi bilan sinab ko'rish
    kerak; murakkab fon (soya, burmali parda, fon rangiga yaqin oq libos) da natija yomon bo'lishi mumkin — `FON_FARQI` sozlanadi.
  - PNG yuklab olish brauzerda bosib sinalmagan. Productionda nginx `/media/` uchun `Access-Control-Allow-Origin` berishi shart
    (canvas eksporti uchun); dev serverda bor.
- Test: `catalog/test_manekin.py` (11 ta). Brauzerda sinov rasmi bilan ko'rildi: qatlam manekinda, surish va saqlash ishladi.

## Bajarildi (30-qism: shartnoma bandlari, statistik hisobotdan tafsilot, primerkada o'lchamlar)
- **Shartnoma shabloni (4.16)**: sozlama `shartnoma_bandlari` — salonning o'z bandlari (15 tagacha, sarlavha + matn); shartnomada
  avtomatik bandlardan keyin, «Shaxsiy ma'lumotlar»dan oldin chiqadi. Avtomatik bandlar (muddat, to'lov, zalog, jarima, avans qaytarish)
  tahrirlanmaydi — ular sozlamalardan yig'iladi (o'z qarorim: aks holda shartnoma matni sozlamalarga zid bo'lib qolishi mumkin).
  Moslash xizmati shartnoma va kvitansiyada alohida qator.
- **FT-18.2 (davomi)**: `GET /api/hisobotlar/h/<nom>/tafsilot/?kalit=&dan=&gacha=` — libos, kategoriya, sotuvchi, salonchi va manba
  hisobotlarida qator nomi bosilsa, shu davrda to'liq to'langan zakazlari ochiladi. Qolgan hisobotlarda (zalog, kassa, bandlik va h.k.)
  qatorning o'zi allaqachon bitta yozuv yoki kun — ularga tafsilot qilinmadi.
- **FT-8.4**: zakaz kartasidagi «Primerka» blokida mijoz o'lchamlari (ko'krak, bel, son, bo'y, oyoq, kiyim o'lchami) tahrirlanadi.
- Jurnal: 300 belgidan uzun qiymat kesib yoziladi (avval uzun sozlama qiymatida xato berishi mumkin edi).

## Bajarildi (31-qism: manekinda aksessuar qatlamlari, FT-5.2)
- `Aksessuar.manekin_rasm` (fonsiz qatlam) va standart joylashuvi; `POST|PATCH|DELETE /api/aksessuarlar/<id>/manekin/`.
  Rasm yuklanganda fon xuddi libosdagidek serverda olib tashlanadi.
- `Manekin.jsx` ko'p qatlamli qilib qayta yozildi: libos + zakazga tanlangan (soni > 0) aksessuarlar; qatlam tanlanadi, suriladi,
  kattalashtiriladi; har qatlamning joylashuvi o'ziga saqlanadi; rasmga eksportda hamma qatlam chiqadi.
  Katalog → Aksessuarlar: «Manekin uchun rasm yuklash», «Manekinda joylash».
- Cheklov: aksessuar joylashuvi aksessuarning o'zida bitta (libosga qarab alohida emas) — fata har xil libosda bir xil joyda turadi.

## Bajarildi (32-qism: filiallar — birinchi versiya, F1, FT-22.8)
- `tenants.Filial` (nomi, manzil, faol); soni tarifdagi `filial_limit` bilan cheklanadi (tarifsiz demo salon cheklanmaydi).
  `GET|POST /api/filiallar/`, `PATCH /api/filiallar/<id>/` (rahbar).
- Qurilma filialga biriktiriladi (`IshonchliQurilma.filial`); shu qurilmadan ochilgan zakaz (`Zakaz.filial`) va qo'shilgan libos
  (`Libos.filial`) shu filialga yoziladi. Rahbar libosni boshqa filialga ko'chiradi (jurnalga yoziladi).
- Filtrlar: katalog, yangi zakazdagi bo'sh liboslar (standart — qurilma filiali; biriktirilmagan libos hamma filialda ko'rinadi),
  zakazlar ro'yxati API (`?filial=`).
- **Ataylab qilinmagan (qaror kerak)**: kassa/smena filial bo'yicha emas — salonda hali ham bitta ochiq smena. Har filialda alohida kassa
  bo'lsa, `Smena` ga filial qo'shish va «salonda bitta ochiq smena» cheklovini «filialda bitta» ga o'zgartirish kerak; bu kassa
  hisobotlari va P&L ga ta'sir qiladi, shuning uchun EZAZ da nechta filial va kassa borligi aniqlangach qilinadi.
  Hisobotlar va dashbordda filial filtri, aksessuar va xodimni filialga biriktirish ham hali yo'q.
- Test: `tenants/test_filial.py` (6 ta).
- Brauzerda sinaldi: filial qo'shish, shartnoma bandi tahrirchisi, manekinda libos + aksessuar (toj) qatlami. Sinalmagan: hisobot qatoridan
  tafsilot (dev bazada to'langan zakaz yo'q), primerkadagi o'lcham formasi, aksessuar rasmini fayl tanlab yuklash, qurilmani filialga biriktirish.
- Manekin: libos qatlamining standart joylashuvi o'zgardi (80%, yelkadan boshlanadi) — avval libos manekin boshini yopib qo'yardi.

## Bajarildi (33-qism: filial bo'yicha kassa, hisobotlarda filial filtri)
- **Qaror (o'zim qabul qildim)**: filial kassasi sozlama bilan yoqiladi — `filial_kassasi` (standart: o'chirilgan, ya'ni salonda bitta
  umumiy kassa, avvalgidek). Yoqilsa: `Smena.filial`; har filialda bittadan ochiq smena (baza cheklovi), umumiy kassada ham bitta.
- To'lov **xodim ishlayotgan smenaga** yoziladi (`cash.services.xodim_smenasi`) — shuning uchun to'lov, zalog, xarajat, jarima kodi
  o'zgarmadi va adashib boshqa filial kassasiga tushmaydi. Xodim bir vaqtda faqat bitta kassada bo'ladi.
- Kassa ekrani qurilma filialining smenasini ko'rsatadi; dashbordda bir nechta kassa ochiq bo'lsa «N ta kassa ochiq».
- Hisobotlarda filial filtri: libos, bo'sh liboslar, bandlik (libos filiali); kategoriya, sotuvchi (zakaz filiali); kunlik kassa (smena filiali).
- Hali yo'q: P&L va dashbordni filial bo'yicha ajratish; xodimni filialga biriktirish; aksessuar donasi filiali.
- Test: `cash/test_filial_kassa.py` (6 ta), `finance/test_statistika.py` → `FilialFiltrTests`.

## Bajarildi (34-qism: aksessuar donasi ta'mir jurnali; dashbord havolalari, FT-19.3)
- `catalog.DonaTamiri`; `GET|POST /api/donalar/<id>/tamir/`, `POST /api/dona-tamir/<id>/tugatish/`. Dona «Ta'mirda» holatiga o'tadi va
  zakazga berilmaydi; bronlari bor dona ta'mirga berilmaydi. Narx «ta'mirlash» xarajatiga tushadi (sotuvchi kiritsa — kassadan, rahbar
  tasdig'i bilan; libos ta'miridagi qoida). Katalog → Aksessuarlar → «Ta'mir» bloki.
- Dashbord: «Bugun», davr va «Oldinda» bloklaridagi ko'rsatkichlar bosilganda tegishli bo'lim ochiladi (FT-19.3).
- Test: `catalog/test_dona_tamir.py` (6 ta). Brauzerda sinalmagan (bu qismdan keyin brauzer sinovi o'tkazilmadi).

## Bajarildi (35-qism: filial bo'yicha foyda/zarar)
- `Xarajat.filial` (bo'sh — butun salon uchun umumiy). Xarajat filial qurilmasidan kiritilsa yoki filial kassasidan to'lansa — shu
  filialga yoziladi.
- `GET /api/hisobotlar/pnl/?oy=&filial=` — **filial natijasi**: filial zakazlari (tushum), filial liboslari (amortizatsiya), filialga
  yozilgan xarajatlar, filial kassasidagi jarimalar, filial zakazlari bo'yicha bonus. Filialga biriktirilmagan (umumiy) xarajat, libos
  va zakazlar filial ko'rinishiga kirmaydi — shuning uchun filiallar yig'indisi butun salon natijasiga teng emas (o'z qarorim: umumiy
  xarajatni filiallarga sun'iy taqsimlamadim).
- Frontend: dashborddagi P&L da filial tanlovi (filial bo'lsa).
- Hali yo'q: P&L qator tafsiloti va 12 oylik grafik filial bo'yicha; dashbordning boshqa bloklari filial bo'yicha; xodim va aksessuar
  donasini filialga biriktirish.
- Test: `finance/test_filial_pnl.py` (4 ta).

## Bajarildi (36-qism: mijozga SMS eslatma, Eskiz.uz)
- `notify/sms.py`: Eskiz API mijozi (tashqi kutubxonasiz), `SmsXabar` jurnali, sozlama `sms_eslatma` (standart: o'chirilgan).
  Ertaga olib ketish (bron holatidagi zakaz, qoldiq summasi bilan) va ertaga qaytarish (berilgan zakaz) haqida mijozga SMS; har zakazga
  har turdagi SMS bir marta (sana ko'chsa — yangi eslatma). Buyruq: `manage.py sms_eslatmalar` (cron: kuniga bir marta).
- **Hisob kiritilmaguncha hech narsa yuborilmaydi**: `.env` da `ESKIZ_EMAIL`, `ESKIZ_PASSWORD`, `ESKIZ_FROM`. Kiritilmagan bo'lsa SMS lar
  jurnalda «kutilmoqda» bo'lib turadi; 1 kundan eski eslatma yuborilmaydi.
- **Haqiqiy shlyuz bilan sinalmagan** — faqat soxta (mock) javoblar bilan. Eskiz API manzillari va maydon nomlari (`/auth/login`,
  `/message/sms/send`, `mobile_phone`, `message`, `from`) xotiradan yozilgan: hisob ochilgach bitta sinov SMS bilan tekshirish kerak.
  Eskiz matn shablonlarini oldindan tasdiqlashni talab qiladi — shablonlar `sms.SHABLONLAR` da.
- `GET /api/sms/` (rahbar) — jurnal; sozlamalarda «Mijozga SMS eslatma» bloki.
- Sotuvchi eslatmalari (FT-14) o'z o'rnida qoladi; SMS — qo'shimcha kanal.
- Test: `notify/test_sms.py` (10 ta).
- 35–36-qismlar brauzerda sinalmadi (brauzer kengaytmasi javob bermadi); API testlari va frontend build bor.

## Bajarildi (37-qism: filiallarning qolgan qismi)
- P&L qator tafsiloti (`/hisobotlar/pnl/tafsilot/?filial=`) va 12 oylik grafik (`/hisobotlar/oylik/?filial=`) filial bo'yicha;
  dashbordda P&L uchun tanlangan filial grafik va tafsilotga ham qo'llanadi.
- `AksessuarDona.filial`: rahbar donani filialga biriktiradi (`PATCH /api/donalar/<id>/ {filial}`). Filial zakaziga aksessuar
  berilganda avval shu filialdagi dona, keyin biriktirilmagani, oxirida boshqa filialdagisi tanlanadi.
- Xodimni filialga biriktirish **ataylab qilinmadi**: filial qurilma (planshet) orqali aniqlanadi, sotuvchi qaysi filial qurilmasidan
  kirsa, o'sha filialda ishlaydi.
- Hali yo'q: dashbordning «Bugun», davr va «Oldinda» bloklari filial bo'yicha.
- Test: `tenants/test_filial2.py` (2 ta). Brauzerda sinalmadi (skrinshot olinmadi — kompyuter ekrani o'chiq yoki oyna yig'ilgan bo'lishi mumkin).

## Bajarildi (38-qism: dashbord filial bo'yicha; dev ilovani telefondan ochish)
- `GET /api/dashbord/?filial=` — «Bugun» (tushum, kassa, olib ketiladi/qaytariladi), davr bloki, «Oldinda» va kutilayotgan daromad shu
  filial bo'yicha; tasdiqlar va ogohlantirishlar butun salon bo'yicha qoladi. Dashbord tepasida bitta filial tanlovi — u grafik va
  foyda/zarar hisobotiga ham qo'llanadi.
- **Dev ilovani shu Wi-Fi dagi telefondan ochish** (ixtiyoriy):
  ```bash
  cd backend && DEV_LAN=1 .venv/Scripts/python manage.py runserver 0.0.0.0:8000
  cd frontend && npm run dev:lan
  # telefonda: http://<kompyuterning tarmoq manzili>:5173
  ```
  `DEV_LAN=1` faqat `DEBUG` rejimida ishlaydi va faqat xususiy tarmoq manzillaridan (192.168.x.x, 10.x.x.x, 172.16–31.x.x) so'rovga
  ruxsat beradi. Frontend API manzilini sahifa ochilgan xostdan oladi (`localhost` da avvalgidek). Windows xavfsizlik devori 8000 va
  5173 portlarga kirishni to'sishi mumkin — qoida qo'shish foydalanuvchi ixtiyorida. Yangi qurilma (telefon) salon loginidan keyin
  rahbar ruxsatini kutadi (Sozlama → Qurilmalar).
- Test: `orders/test_dashbord_filial.py` (3 ta). Brauzerda sinalmadi.

## Bajarildi (39-qism: integratsiyalar admin sozlamalarida)
Talab: tashqi xizmatlar admin sozlamalaridan kiritilsin va **tizim ularsiz ham to'liq ishlasin**.
- `tenants.Integratsiya` (salon bo'yicha, hammasi ixtiyoriy); `GET|PATCH /api/integratsiyalar/` (faqat rahbar);
  frontend: Sozlama → «Integratsiyalar» (`components/Integratsiyalar.jsx`).
- **Telegram**: salon o'z bot tokenini kiritadi; bo'lmasa platforma boti (`.env`), u ham bo'lmasa Telegram o'chiq — xabarlar jurnalda
  qoladi, rahbar faqat PIN bilan kiradi. `telegram_bot` buyrug'i endi platforma va barcha salon botlarini navbat bilan tinglaydi,
  tokenlar ro'yxatini har aylanishda yangilaydi (qayta ishga tushirish shart emas). Boti yo'q salon xabari boshqa salon boti orqali ketmaydi.
- **SMS (Eskiz)**: salonning o'z hisobi (email, parol, yuboruvchi nomi) va o'z shablonlari; bo'lmasa platforma hisobi; u ham bo'lmasa
  SMS lar jurnalda kutadi.
- **Click / Payme**: service/merchant ID kiritilsa, to'lov oynasida mijozga beriladigan **to'lov havolasi** chiqadi
  (`GET /api/zakazlar/<id>/tolov-havola/`). To'lovni avtomatik tasdiqlash (webhook) **yo'q**: sotuvchi merchant kabinetida ko'rib, kassada
  odatdagidek qabul qiladi. Maxfiy kalitlar so'ralmaydi va saqlanmaydi (havola uchun faqat ochiq ID lar kerak).
- **Soliq**: salon foizi va buxgalter xulosasi izohi; bo'sh — standart 4%. P&L shu foiz bilan hisoblanadi.
- **Manekin**: fonni ajratish sezgirligi (8–120, standart 38) — haqiqiy rasmlarga moslash uchun.
- **Instagram, onlayn kassa, 1C**: avtomatik almashinuv yo'q. Salon Instagram havolasi saqlanadi; «fiskal chek eslatmasi» yoqilsa,
  to'lovdan keyin sotuvchiga eslatma matni chiqadi.
- **Maxfiylik**: bot tokeni va Eskiz paroli API orqali qaytarilmaydi (faqat «kiritilgan»), jurnalga va salon arxiviga yozilmaydi.
  Bazada ochiq matnda saqlanadi (server ularni ishlatishi kerak) — baza zaxira nusxalarini shunga qarab himoyalang.
- **Tekshirilmagan**: Click va Payme havola formatlari xotiradan yozilgan — merchant ID kiritilgach bitta sinov to'lovi bilan tekshirish kerak.
  Eskiz va Telegram haqiqiy xizmat bilan sinalmagan (faqat soxta javoblar). Brauzerda bosib sinalmagan.
- Test: `tenants/test_integratsiya.py` (16 ta).

## Bajarildi (40-qism: TZ bilan solishtirishda topilgan bo'shliqlar)
TZ dagi 136 ta FT talabi kod va shu fayl bilan solishtirildi; quyidagilar amalda yo'q ekan va qo'shildi:
- **FT-12.5 kunlik zalog tekshiruvi**: `cash.ZalogTekshiruvi`; `GET|POST /api/kassa/zaloglar/` — salonda saqlanayotgan hujjat/tillo
  zaloglar, sotuvchi har birini «joyida» yoki «yo'q» (izoh majburiy) deb belgilaydi. «Yo'q» — rahbarga darhol xabar. Smena
  tekshirilmagan zalog bilan yopilsa, yopiladi, lekin rahbarga xabar boradi va smenada `zalog_tekshirilmagan` yoziladi
  (o'z qarorim: yopishni to'smadim — kassa ochiq qolib ketmasligi muhimroq).
- **FT-12.6 inkassatsiya**: kassa ekranida forma (API avvaldan bor edi, ekrani yo'q edi).
- **FT-12.11 yopilgan smenani tuzatish**: `GET /api/kassa/smenalar/`, `PATCH /api/kassa/smenalar/<id>/` — faqat rahbar; fakt qoldiq va
  izoh, farq qayta hisoblanadi, jurnalga yoziladi. Kassa ekranida «Smenalar tarixi».
- **FT-11.1 chegirma summada**: chegirma formasida foiz/summa tanlovi, chegirma summasi va yangi jami ko'rsatiladi (backend avvaldan bor edi).
- **Rahbar uchun xarajatlar ekrani** (avval rahbar bino ijarasi kabi kassadan tashqari xarajatni faqat kassa ekranidan, smena ochiq
  bo'lganda kirita olardi): «Hisobot» → «Xarajatlar» — kiritish (istalgan modda va sana), oy bo'yicha ro'yxat, tasdiqlash.
- **FT-13.1 xarajat moddalari**: `finance.XarajatModdasi` — rahbar o'z moddasini qo'shadi (to'g'ridan-to'g'ri yoki operatsion);
  `Xarajat.modda` da `m<id>` kodi. `GET|POST /api/xarajat-moddalari/`. Modda o'chirilmaydi — nofaol qilinadi; turi o'zgartirilmaydi.
- **FT-13.3 doimiy oylik xarajatlar**: `finance.DoimiyXarajat`; har oy bitta qoralama (tasdiq kutayotgan xarajat) yaratiladi — rahbar
  xarajatlar ro'yxatini ochganda (cron shart emas). Rahbar summani o'zgartirib tasdiqlaydi yoki rad etadi.
- Tekshirib ko'rildi, bor ekan (faqat FT raqami yozilmagan): FT-1.3, 2.1, 3.1, 3.3, 4.1, 9.1, 12.1, 12.2, 12.4, 13.4, 14.3, 16.2, 19.4, 21.3.
- Test: `cash/test_tekshiruv.py` (12 ta). Brauzerda sinalmadi.
- **Tuzatildi (vaqt mintaqasi)**: hisobotlarda libos yaratilgan sana, jarima va bekor qilish sanasi UTC bo'yicha olinardi — Toshkent
  vaqti bilan 00:00–05:00 oralig'ida bir kunga xato chiqardi (to'liq test yarim tundan keyin ishga tushganda aniqlandi). Endi mahalliy
  vaqt bo'yicha. To'liq to'plam: 580 tadan 579 tasi o'tdi, shu bitta xato tuzatilgach faqat finance va sozlamalar testlari (85 ta) qayta o'tkazildi.
- Dev baza uchun sinov platforma admini yaratildi (`egasi`); demo kirish ma'lumotlari `demo_ezaz` buyrug'ida.

## Qolgan ishlar (2026-10-09 holatiga)
Kod tayyor — faqat qiymat kiritish kerak (Sozlama → «Integratsiyalar»; kiritilmasa ham tizim ishlaydi):
1. Telegram bot tokeni va nomi (BotFather).
2. Eskiz email/parol; shablonlarni Eskiz kabinetida tasdiqlatish; bitta sinov SMS.
3. Click service/merchant ID, Payme merchant ID; bitta sinov to'lovi bilan havolani tekshirish.
4. Soliq foizi (buxgalter xulosasi).
5. Manekin sezgirligini salonning 10 ta haqiqiy rasmi bilan sozlash (FT-5.6).

Kod bilan qilinadigan, hali qilinmagan:
6. Click/Payme to'lovini avtomatik tasdiqlash (webhook) — merchant shartnomasi va sinov muhiti kerak.
7. Manekin rasmini bot orqali mijozga to'g'ridan-to'g'ri yuborish (FT-5.4).
8. Instagram, 1C va onlayn kassa bilan avtomatik almashinuv (3-bosqich, tashqi tizimlar).

Ishga tushirishdan oldin (foydalanuvchi tomonida):
- `manage.py platforma_admin <login>` — platforma egasi hisobi.
- Cron: `bronlarni_tozalash` (har 15 daqiqa), `eslatmalarni_yuborish` (har soatda), `kunlik_hisobot` (har 15 daqiqa),
  `sms_eslatmalar` (kuniga bir marta, SMS yoqilgan bo'lsa),
  ixtiyoriy `chiqqan_salonlar --ochirish`.
- Production: nginx `/media/` uchun CORS sarlavhasi (manekin rasmini eksport qilish uchun).
- Kod hali **commit qilinmagan** (faqat `git add -A`).

## Hal qilinmagan (TZ ziddiyatlari)
- 1-bosqichda P&L bor, lekin Xarajatlar moduli 2-bosqichda (FT-12.3 kassada xarajat kiritishni talab qiladi).
- Rahbar Telegram-kod bilan kirishi (FT-1.1) — Telegram 2-bosqichda; hozircha faqat PIN.
- Eslatmalar (FT-14.1) "majburiy", lekin 2-bosqichda.
- Soliq qaysi oyga tushishi — buxgalter xulosasi kutilmoqda (0-bosqich).

## Bajarildi (43-qism: reklama sahifasi — Lusion uslubidagi qasr, kelinlar gologrammasi, o'yin kartalari) — 2026-10-11
Foydalanuvchi lusion.co/about effektlarini kelin/qasr mavzusida xohladi; har bosqich brauzerda (localhost:5173, ~1400×850) birga ko'rib sozlandi.
Brend: EZAZ — `--serif` (Casagrande Deco/Forum), `--kursiv` (Cormorant Garamond), `--tilla #e4c196`, `--oq #fbf6ee`, `--siyoh #0e1a2b`, `--kok #2f496e`.
Hamma qism keng ekran uchun: `@media (min-width:900px) and (min-aspect-ratio:11/10)`; telefon/tik ekranda soddalashtirilgan ko'rinish.

**1) Bosh kadr — `QasrVideo.jsx` + `gulbargSahna.js` + `reklama-qasr.css`** (`Reklama.jsx` da `<canvas className="rk-sahna">` dan keyin `{jonli && <QasrVideo />}`)
- `public/video/qasr.mp4` — Artlist Seedance 2.5 (15 s, 480p qoralama): yorug' hashamatli saroy zali, gulbarg girdobidan kamera orqaga chekinadi.
  Video o'ynamaydi — `currentTime` aylantirishga bog'langan (lerp 0.12, `!v.seeking` sharti bilan), `BOSHLANISH = 4.3` s dan.
- `gulbargSahna.js` — WebGL1 gulbarglar, kursor bilan prujina fizikasi; `gulbargYarat(canvas)` → `{sur(p), yop()}`.
- Bosh kadr balandligi 760vh; ssenariy (`--p`): 0–45% WEDDY harflari yiqiladi; 40–48% «A'zo bo'lish/Kirish» tugmalari chiqadi; 59–66% blur bilan ketadi;
  64–72% saroy xiralashadi (`.rk-qasr-xira`, `--bp`); 70–89% «Kelin liboslari / salonlari uchun / ijara tizimi» + o'ng blok qatorma-qator chiqadi.
- Bosh kadrdan keyin video o'chmaydi: `--chiq` bilan ko'k tus (`.rk-qasr-tus`, mix-blend color) va gumbazdan nur (`.rk-qasr-nur`, screen, «nafas»).
- Toj shakli olib tashlandi; `reklamaSahna.js` shakllar: `[libos, chang, uzuklar, grafik, chang, chang]` (toj va kalendar → chang). Arka slaydi olib tashlandi.

**2) Kelinlar — `Kelinlar.jsx` + `gologramma.js` + `kelinlar.css`** (Lusion TEAM bo'limi uslubida)
- Sticky bo'lim 520vh, 5 obraz (Sirena, Malika, Nafis to'r, Zamonaviy, Orzu) aylantirish bilan almashadi; portretni bosish → keyingisi.
- Fon: `public/kelinlar/saroy.jpg` (yorug' saroy, blur) + aura; harflar yomg'iri (2D canvas); HUD `[[ 00N ]]`, keng «KELINLAR» sarlavha,
  kvadratchali bosh harf, izoh.
- `gologramma.js`: rasm yorug'ligidan 22 000 nuqta (halftone), almashishda eskisi chapga sochiladi, yangisi o'ngdan yig'iladi; kursor to'lqini,
  glitch tasmalari. `gologrammaYarat(canvas, rasmlar)` → `{soni, tanla(i), yop()}`; rasm — satr yoki `{src, kesim:[x,y,w,h]}`.
- Rasmlar: `public/kelinlar/1–5.jpg` (560px) — Artlist Nano Banana 2 da yaratilgan 2×2 kollajdan kesilgan (1–4) va «yurayotgan kelin» (5).

**3) O'yin kartalari — `OyinKartalar.jsx` + `kartalar.css`** (Lusion «Area of Expertise» uslubida; eski kino bo'limi — Bron/Zalog/Foyda matnlari,
`libos_bron.mp4` — shu bilan almashtirildi; `KADRLAR`, `KADR_CHOQQI` o'chirildi)
- Komponent nomi `OyinKartalar` (Reklama.jsx da galereya uchun boshqa `Kartalar` bor), sinflar `rk-okarta-*` (galereyaning `.rk-karta` sinfi bilan to'qnashmasin), id `tashvishlar`.
- Sticky 460vh, JS o'zgaruvchilari: bo'limda `--fan` (10–40% yoyilish), `--sarl` (sarlavha ketishi), `--lenta` (15–80% tilla lenta SVG chiziladi),
  `--tek` (70–88% tekislanish), `--ket` (93–100% so'nish); har kartada `--flip` (40–56%, 50–66%, 60–76% ag'darilish), `--mx/--my` (kursor egilishi).
  Kartani bosish — qo'lda ag'darish.
- Orqa tomon: to'q ko'k, tilla art-deko naqsh (SVG), arkada kelin rasmi (`/kelinlar/1–3.jpg`). Old tomon: fil suyagi, raqam, nom, 5×7 piksel harf (B/Z/F),
  kursiv shior, nuqtali qatorlar, pastda teskari nom.
- `Reklama.jsx`: `<div id="sahnalar" style={{position:'relative'}}>` ichida ikki `rk-langar data-t="1"` (fon — chang) + `<Kelinlar />` + `<OyinKartalar />`.
  «Pastga aylantiring» havolasi hali `#sahnalar` ga boradi.

**Ish usuli bo'yicha eslatmalar**
- Artlist/imgix ga cloud konteynerdan ham, foydalanuvchi VM sidan ham kirish yo'q (proxy 403). Rasmlar brauzerdan (canvas → blob) olindi:
  `vite.config.js` ga vaqtincha `/__yukla` middleware qo'shilib `public/kelinlar/` ga yozildi, keyin config asl holiga qaytarildi.
- Linux VM da `npm run build` ishlamaydi (node_modules Windows uchun o'rnatilgan) — tekshiruv faqat Windows'dagi dev server orqali.
- Seedance boshlang'ich+oxirgi kadr bilan «morphing» berdi — yaxshi prompt va yorug' saroy kadrlari bilan 15 s versiya ishladi.
- Lint/build bu qismda ishga tushirilmagan; dev serverda konsol xatosiz.
