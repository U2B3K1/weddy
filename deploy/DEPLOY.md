# Libosa — production deploy qo'llanmasi

Bu hujjat **Libosa** (weddy) loyihasini Ubuntu VPS'ga (nginx + PostgreSQL + systemd)
to'liq o'rnatish tartibini tushuntiradi. Domain: **libosa.uz**.

---

## 0. Server talablari

| Narsa | Talab | Izoh |
|---|---|---|
| OS | Ubuntu 24.04 / 26.04 LTS | 26.04 da Python 3.13 keladi — mos |
| RAM | 1 GB (min) | 2 GB tavsiya etiladi |
| Disk | 10 GB + | media (rasmlar) uchun zahira |
| Port | 80, 443 ochiq | SSH 22 albatta |
| Domen | libosa.uz A-record → server IP | `www` ham bo'lsa yaxshi |
| DB | PostgreSQL 15+ | |
| Python | 3.11+ | venv bilan |

Asosiy dasturlar (serverda o'rnatiladi): `python3-venv`, `python3-dev`, `build-essential`,
`libpq-dev`, `postgresql`, `nginx`, `certbot python3-certbot-nginx`, `git`.

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential libpq-dev \
    postgresql nginx git certbot python3-certbot-nginx
```

---

## 1. GitHub'ga kodni chiqarish (mahalliy kompyuterda)

`weddy/` — o'z repozitoriysi. GitHub'da **Libosa** repo oching, so'ng:

```bash
git -C weddy remote add origin https://github.com/U2B3K1/weddy.git
git -C weddy add .
git -C weddy commit -m "feat: production deploy config qo'shildi"
git -C weddy push -u origin master
```

> `.env` fayllari `.gitignore` da — serverga git orqali bormaydi. To'g'ri.

---

## 2. Serverda foydalanuvchi va papka

```bash
sudo useradd --system --home /var/www/libosa --shell /bin/bash libosa
sudo mkdir -p /var/www/libosa
sudo chown -R libosa:libosa /var/www/libosa
sudo adduser libosa www-data     # nginx media/static o'qiy olishi uchun
```

## 3. Kodni olish

```bash
cd /var/www
sudo -u libosa git clone -b master https://github.com/U2B3K1/weddy.git libosa
# agar repo allaqachon yaratilgan bo'lsa:
#   sudo rm -rf libosa && sudo -u libosa git clone -b master https://github.com/U2B3K1/weddy.git libosa
```

---

## 4. Python venv va bog'liqliklar

```bash
cd /var/www/libosa
sudo -u libosa python3 -m venv venv
sudo -u libosa venv/bin/pip install --upgrade pip
sudo -u libosa venv/bin/pip install -r backend/requirements.txt
```

## 5. PostgreSQL

```bash
sudo -u postgres psql
# psql ichida:
CREATE USER libosa WITH PASSWORD 'KUCHLI_PAROL';
CREATE DATABASE libosa OWNER libosa;
\q
```

---

## 6. `.env` (muhim — sir saqlash)

```bash
sudo -u libosa cp /var/www/libosa/deploy/.env.production.example /var/www/libosa/backend/.env
sudo -u libosa nano /var/www/libosa/backend/.env
```

Kamida shularni to'ldiring:
- `SECRET_KEY` — uzun tasodifiy kalit. Olish: `venv/bin/python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DATABASE_URL` — `postgres://libosa:KUCHLI_PAROL@127.0.0.1:5432/libosa`
- `TELEGRAM_BOT_TOKEN`, `ESKIZ_EMAIL`, `ESKIZ_PASSWORD` — bor bo'lsa

Fayl ruxsatini toraytirish:

```bash
sudo chown libosa:libosa /var/www/libosa/backend/.env
sudo chmod 600 /var/www/libosa/backend/.env
```

---

## 7. Migratsiya + statik + superuser

```bash
cd /var/www/libosa/backend
sudo -u libosa ../venv/bin/python manage.py migrate
sudo -u libosa ../venv/bin/python manage.py collectstatic --noinput
sudo -u libosa ../venv/bin/python manage.py createsuperuser
```

---

## 8. Frontend build

```bash
cd /var/www/libosa/frontend
sudo -u libosa npm install
sudo -u libosa npm run build      # dist/ yaratadi, VITE_API_URL=/api (same-origin)
```

> `npm` yo'q bo'lsa: `sudo apt install -y nodejs npm` yoki Node 20+ LTS qo'ying.

---

## 9. systemd servislari

```bash
sudo cp /var/www/libosa/deploy/gunicorn.service    /etc/systemd/system/libosa.service
sudo cp /var/www/libosa/deploy/telegram_bot.service /etc/systemd/system/libosa-telegram.service

sudo systemctl daemon-reload
sudo systemctl enable --now libosa.service
sudo systemctl enable --now libosa-telegram.service

# holatni tekshirish:
sudo systemctl status libosa.service
sudo journalctl -u libosa.service -f
```

---

## 10. nginx

```bash
sudo cp /var/www/libosa/deploy/nginx-libosa.uz.conf /etc/nginx/sites-available/libosa.uz
sudo ln -s /etc/nginx/sites-available/libosa.uz /etc/nginx/sites-enabled/libosa.uz
sudo rm -f /etc/nginx/sites-enabled/default      # eski default sayt
sudo nginx -t
sudo systemctl reload nginx
```

> Birinchi `nginx -t` da `ssl_certificate` fayli topilmasligi mumkin — HTTPS blokini
> vaqtincha izohlab qo'ying, yoki avval certbot ishga tushiring (11-qadam), so'ng qayta `nginx -t`.

## 11. HTTPS (Let's Encrypt)

```bash
sudo certbot --nginx -d libosa.uz -d www.libosa.uz
sudo certbot renew --dry-run     # avtomatik yangilanishni tekshirish
```

certbot `ssl_certificate`/`ssl_certificate_key` qatorlarini o'zi to'ldiradi va
HTTP→HTTPS o'tishni ham sozlaydi.

---

## 12. Cron (rejalashtirilgan ishlar)

```bash
sudo timedatectl set-timezone Asia/Tashkent
sudo mkdir -p /var/log
sudo touch /var/log/libosa-cron.log
sudo chown libosa:libosa /var/log/libosa-cron.log
sudo -u libosa crontab /var/www/libosa/deploy/crontab.txt
sudo -u libosa crontab -l    # tekshirish
```

---

## 13. Tekshirish ro'yxati

- [ ] `https://libosa.uz` ochiladi (frontend)
- [ ] `https://libosa.uz/adminaka/` ochiladi (Django admin)
- [ ] `/api/` so'rovlari ishlaydi (login, salon kirishi)
- [ ] Rasm yuklash `/media/` orqali ko'rinadi
- [ ] `journalctl -u libosa.service` da xatolik yo'q
- [ ] Telegram bot javob beradi (agar token berilgan bo'lsa)
- [ ] `sudo systemctl status libosa libosa-telegram` — `active (running)`

---

## 14. Yangilash (har deploy'da)

```bash
cd /var/www/libosa
sudo -u libosa git pull
sudo -u libosa venv/bin/pip install --upgrade pip          # o'rnatuvchining o'zi ham zaifliksiz bo'lsin
sudo -u libosa venv/bin/pip install -r backend/requirements.txt
cd backend
sudo -u libosa ../venv/bin/python manage.py migrate
sudo -u libosa ../venv/bin/python manage.py collectstatic --noinput
cd ../frontend
sudo -u libosa npm install
sudo -u libosa npm run build
sudo systemctl restart libosa.service libosa-telegram.service
```

Bir buyruq bilan (root sifatida):

```bash
cd /var/www/libosa && sudo -u libosa git pull && \
sudo -u libosa venv/bin/pip install --upgrade pip && \
sudo -u libosa venv/bin/pip install -r backend/requirements.txt && \
cd backend && sudo -u libosa ../venv/bin/python manage.py migrate && \
sudo -u libosa ../venv/bin/python manage.py collectstatic --noinput && \
cd ../frontend && sudo -u libosa npm install && sudo -u libosa npm run build && \
sudo systemctl restart libosa.service libosa-telegram.service
```

### nginx sozlamasi o'zgargan bo'lsa

`deploy/nginx-libosa.uz.conf` o'zgargan deployda (masalan, 2026-11-10: siqish va xavfsizlik sarlavhalari qo'shildi)
serverdagi nusxa ham yangilanadi — `git pull` uni o'zi almashtirmaydi:

```bash
sudo cp /etc/nginx/sites-available/libosa.uz /etc/nginx/sites-available/libosa.uz.zaxira   # eski nusxa
sudo cp /var/www/libosa/deploy/nginx-libosa.uz.conf /etc/nginx/sites-available/libosa.uz
sudo nginx -t && sudo systemctl reload nginx
# `nginx -t` xato bersa — reload qilinmaydi (sayt eski sozlamada ishlayveradi); zaxirani qaytaring:
#   sudo cp /etc/nginx/sites-available/libosa.uz.zaxira /etc/nginx/sites-available/libosa.uz
```

Tekshirish (istalgan kompyuterdan):

```bash
curl -sI -H "Accept-Encoding: gzip" https://libosa.uz/ | grep -iE "content-encoding|content-security|strict-transport"
# JS fayli siqilganmi (Content-Encoding: gzip chiqishi kerak):
curl -s https://libosa.uz/ | grep -oE '/assets/index-[A-Za-z0-9_-]+\.js' | head -1 |   xargs -I{} curl -sI -H "Accept-Encoding: gzip" https://libosa.uz{} | grep -iE "content-encoding|cache-control"
```

Keyin saytni brauzerda ochib, kirish → Liboslar (rasmlar ko'rinishi) → Zakazlar ni bir marta aylanib chiqing.
Biror narsa ko'rinmay qolsa (brauzer konsolida «Content Security Policy» xatosi) — zaxira nusxani qaytaring.

Deploy'dan **oldin** (mahalliy kompyuterda) kutubxona zaifliklari tekshiriladi. Topilsa — lock/requirements
mahalliy tuzatilib push qilinadi. Serverda `npm audit fix` ishlatilmaydi: `package-lock.json` o'zgarib,
keyingi `git pull` to'qnashadi.

```bash
cd frontend && npm audit                                                 # frontend
cd ../backend && .venv/Scripts/python -m pip_audit -r requirements.txt   # backend (avval: pip install pip-audit)
```

---

## 15. Zaxira (backup)

Zakaz va to'lovlar faqat bazada — disk buzilsa hammasi yo'qoladi. `deploy/zaxira.sh` har kuni bazani
(`pg_dump -Fc`, 14 kun saqlanadi), yakshanba kunlari media papkasini (4 hafta) `/var/backups/libosa/` ga yozadi.
Bir marta o'rnatish (root sifatida):

```bash
chmod +x /var/www/libosa/deploy/zaxira.sh
echo '30 3 * * * root /var/www/libosa/deploy/zaxira.sh >> /var/log/libosa-zaxira.log 2>&1' > /etc/cron.d/libosa-zaxira
/var/www/libosa/deploy/zaxira.sh          # hozir bir marta sinab ko'ring
ls -lh /var/backups/libosa/
```

Tiklash (avval saytni to'xtating — `systemctl stop libosa.service libosa-telegram.service`):

```bash
sudo -u postgres pg_restore --clean --if-exists -d libosa /var/backups/libosa/baza-YYYY-MM-DD.dump
tar -xzf /var/backups/libosa/media-YYYY-MM-DD.tar.gz -C /var/www/libosa/backend/
```

**Telegram orqali egaga.** Baza nusxasi har kuni platforma egasining Telegramiga ham yuboriladi, nusxa olinmasa —
xato xabari boradi. Buning uchun ega botga ulangan bo'lishi kerak (platforma paneli → Telegram → ulash). Nusxada
mijozlar telefoni, hujjat raqamlari va integratsiya kalitlari bor, shuning uchun uni parol bilan shifrlang:

```bash
echo "ZAXIRA_PAROL='bu-yerga-uzun-parol'" > /etc/libosa-zaxira.conf && chmod 600 /etc/libosa-zaxira.conf
# Parolni alohida joyga yozib qo'ying — usiz nusxa ochilmaydi. Ochish:
#   openssl enc -d -aes-256-cbc -pbkdf2 -in baza-YYYY-MM-DD.dump.enc -out baza.dump
```

Cheklovlar: Telegram 50 MB dan katta faylni olmaydi (baza o'sib ketsa egaga ogohlantirish keladi — o'shanda rclone
kerak); rasmlar (media) Telegramga yuborilmaydi. O'chirish: shu faylga `ZAXIRA_TELEGRAM=0`.

**Server xatolari ham egaga boradi:** har bir 500 javob va ilova xatosi Telegramga qisqa xabar bo'lib keladi
(manzil, xato turi, kod qatori; so'rov mazmuni yuborilmaydi). Bir xil xato 30 daqiqada bir marta, jami 10 daqiqada
10 tadan ko'p emas. O'chirish: `.env` ga `XATO_XABARI=False`.

Bot «🩺 Holat» tugmasi oxirgi zaxira nusxa qachon yuborilganini ko'rsatadi (36 soatdan eski bo'lsa ogohlantiradi).

**Nusxani server tashqarisiga ham yuboring** — server butunlay ishdan chiqsa, shu yerdagi nusxa ham yo'qoladi.
Eng oddiy yo'li: `rclone` (Google Drive, Yandex Disk, S3) sozlab, `zaxira.sh` oxiridagi izohdagi qatorni yoqish.
Oyda bir marta tiklashni sinov bazasida tekshirib ko'ring — tekshirilmagan nusxa nusxa emas.

---

## 16. Tashqi monitoring (serverdan mustaqil)

Server butunlay o'chsa, bot ham jim bo'ladi — shuning uchun uzilishni **boshqa joyda** ishlaydigan bepul uptime
xizmati kuzatishi kerak (UptimeRobot, Better Stack, HetrixTools va h.k. — istalgani). Hisobni platforma egasi o'zi ochadi.

Xizmatda bitta HTTP(S) tekshiruv yarating:

- Manzil: `https://libosa.uz/api/sogliq/`
- Oraliq: 5 daqiqa
- Kutilgan javob: HTTP 200 (matnida `"holat": "ok"`)
- Ogohlantirish: Telegram (xizmatning o'z boti) va zaxira sifatida email

`/api/sogliq/` qachon 503 qaytaradi:

- baza ishlamasa (`"baza": false`);
- fon vazifasi to'xtab qolsa (`"fon": false`): bot jarayoni 5 daqiqa, bronlarni tozalash 30 daqiqa, kunlik hisobot
  45 daqiqa, eslatmalar 2,5 soat ishlamasa. Hali bir marta ham ishlamagan vazifa hisobga olinmaydi.

Bundan tashqari bot va soatlik cron bir-birini kuzatadi: biri to'xtasa, ikkinchisi platforma egasining Telegramiga
yozadi (`apps/notify/yurak.py`); botdagi «🩺 Holat» hammasini bitta kartada ko'rsatadi.

Deploy paytida bot bir necha soniya to'xtaydi — 5 daqiqadan qisqa bo'lsa ogohlantirish chiqmaydi.

## 17. Muhim eslatmalar

1. **`.env` hech qachon gitga kirmaydi.** `.env.example` bilan ishlang.
2. `DEBUG=False` productionda shart. Bu `settings.py` dagi HTTPS xavfsizlik blokini ham
   faollashtiradi (xavfsiz cookie + CSRF).
3. `ALLOWED_HOSTS` ga faqat haqiqiy domenlar yozing — `*` productionda xavfli.
4. Bot tokeni API javoblarida va loglarda **chiqmasligi kerak** — kod shuni ta'minlaydi.
5. Frontend `VITE_API_URL=/api` bo'lgani uchun port 8000 tashqariga ochilmaydi — faqat nginx.

## 18. Akademiya (academy.libosa.uz)

Akademiya — o'sha ilova va o'sha backend, alohida manzilda. Server so'rov qaysi hostdan kelganiga qaraydi:
`academy.libosa.uz` dan kelgan so'rov faqat o'quv saloni bilan ishlaydi, `libosa.uz` da esa o'quv saloni ochilmaydi
(`backend/apps/akademiya/`). Alohida baza, alohida xizmat yoki alohida build kerak emas.

Birinchi marta yoqish (bir martalik):

1. **DNS.** Domen boshqaruvida `academy` uchun `A` yozuvi — serverning IP manzili (`libosa.uz` dagi bilan bir xil).
   Tarqalganini tekshirish: `dig +short academy.libosa.uz`.
2. **`.env`.** `ALLOWED_HOSTS` ga `academy.libosa.uz` qo'shiladi:

   ```bash
   sudo -u libosa nano /var/www/libosa/backend/.env     # ALLOWED_HOSTS=libosa.uz,www.libosa.uz,academy.libosa.uz
   ```

3. **Kod va migratsiya** — odatdagi yangilash (§14). Yangi migratsiyalar: `tenants/0047`, `akademiya/0001`–`0003`.
4. **nginx.** `deploy/nginx-libosa.uz.conf` da `server_name` ga `academy.libosa.uz` qo'shilgan — serverdagi nusxani
   yangilang (§14, «nginx sozlamasi o'zgargan bo'lsa»), keyin `sudo nginx -t`.
5. **Sertifikat.** Mavjud sertifikatga yangi nom qo'shiladi:

   ```bash
   sudo certbot --nginx --expand -d libosa.uz -d www.libosa.uz -d academy.libosa.uz
   sudo systemctl reload nginx
   ```

6. **Cron.** `deploy/crontab.txt` ga `oquv_tozalash` qatori qo'shilgan — `crontab /var/www/libosa/deploy/crontab.txt`.

Tekshirish:

- `https://academy.libosa.uz` — kirish filmi, keyin «Boshlash →» tugmali bosh sahifa chiqadi (salon logini so'ralmaydi);
  «Boshlash» mehmon sifatida bepul darslarga olib kiradi.
- `https://libosa.uz` da kirib, yuqoridagi ism → «Akademiya»: yangi tabda o'quv saloni ochiladi, o'ngda pastda
  oltin «O'quv saloni» tugmasi turadi.
- `curl -s -o /dev/null -w '%{http_code}
' -X POST https://academy.libosa.uz/api/auth/salon-login/` → `403`
  (akademiya manzilidan haqiqiy salonga kirib bo'lmaydi).

O'quv salonlari platforma panelidagi salonlar ro'yxatiga, kunlik hisobot, eslatma va SMS buyruqlariga kirmaydi;
ulardan SMS va Telegram xabari chiqmaydi. 30 kun ochilmagan o'quv saloni `oquv_tozalash` bilan o'chadi —
o'quvchining dars natijalari saqlanib qoladi.


---

## 19. Cloudflare (foydalanuvchi IP bloklaridan himoya)

**Nima uchun.** Hostinger tarmoq himoyasi «yomon nom» olgan IP manzillarni o'zi to'sadi va biz uni boshqara olmaymiz.
2026-11-26 da egasining uy interneti (O'zbektelekom) shunday bloklandi: bu manzilni ko'p abonent birga ishlatadi (CGNAT)
va boshqalarning harakati uchun u shikoyatlar bazasida yomon nom olgan. Sayt, SSH va Web console ochilmadi, mobil
internetdan esa ochildi; Hostinger blokni olib tashlashni rad etdi. Shu provayder orqali ishlaydigan salonlar ham shunday
bloklanishi mumkin. Cloudflare orqasida foydalanuvchi Cloudflare'ga ulanadi, Hostinger esa faqat Cloudflare manzillarini
ko'radi.

### 19.1 Server (nameserver almashtirishdan OLDIN)

`deploy/nginx-libosa.uz.conf` boshida `set_real_ip_from` (Cloudflare manzillari) va `real_ip_header CF-Connecting-IP`
bor: Cloudflare orqali kelgan so'rovda nginx mijozning haqiqiy IP manzilini oladi. Busiz hamma Cloudflare manzili
bo'lib ko'rinardi va login himoyasi (IP bo'yicha 5 ta xato) bir odamning xatosi uchun boshqalarni ham bloklardi.
Cloudflare'siz kelgan so'rovga ta'sir qilmaydi — shuning uchun oldindan qo'yish xavfsiz. `git pull` dan keyin:

```bash
sudo cp /etc/nginx/sites-available/libosa.uz /etc/nginx/sites-available/libosa.uz.zaxira
sudo cp /var/www/libosa/deploy/nginx-libosa.uz.conf /etc/nginx/sites-available/libosa.uz
sudo nginx -t && sudo systemctl reload nginx
# `nginx -t` xato bersa — zaxirani qaytaring:
#   sudo cp /etc/nginx/sites-available/libosa.uz.zaxira /etc/nginx/sites-available/libosa.uz
```

Cloudflare manzillari ro'yxati: https://www.cloudflare.com/ips/ — yiliga bir-ikki marta conf dagi ro'yxat bilan solishtiring.

### 19.2 Cloudflare paneli (bepul tarif)

1. cloudflare.com da hisob oching → **Domains → Overview → Add domain** → `libosa.uz`, «Quick scan for DNS records» →
   tarif **Free**. AI botlarni to'sish haqida so'rasa — to'smang (saytda `llms.txt` bor: AI qidiruvlarida ko'rinish uchun).
2. **DNS yozuvlarini tekshiring.** Cloudflare hozirgi yozuvlarni o'zi ko'chiradi, lekin hammasini topmasligi mumkin.
   2026-11-26 dagi holat (DNS hozir webspace.uz da: `dns1`–`dns4.webspace.uz`) — shu ro'yxat bilan solishtiring:

   | Tur | Nom | Qiymat | Proxy (hozircha) |
   |---|---|---|---|
   | A | `libosa.uz` (@) | `187.7.77.233` | DNS only (kulrang bulut) |
   | CNAME | `www` | `libosa.uz` | DNS only |
   | A | `academy` | `187.7.77.233` | DNS only |
   | TXT | `libosa.uz` (@) | `google-site-verification=…` (Google Search Console, o'zgarishsiz) | — |
   | MX | `libosa.uz` (@) | `libosa.uz` | — |

   MX — webspace.uz shablonidan qolgan yozuv: serverda pochta yo'q, `@libosa.uz` pochtasi hozir ham ishlamaydi.
   Cloudflare «pochta ishlamasligi mumkin» deb ogohlantirsa — e'tibor bermang (yoki MX ni o'chiring), hech narsa o'zgarmaydi.

   **Uchala sayt yozuvi hozircha DNS only bo'lsin** (Cloudflare ularni o'zi Proxied qilib qo'ygan bo'lsa — bulutchani bosib
   kulrang qiling). Cloudflare o'z HTTPS sertifikatini domen faollashgandan keyin 15 daqiqa–24 soat ichida beradi; undan
   oldin Proxied qilinsa, saytga kirganlar sertifikat xatosini ko'radi va HSTS tufayli uni chetlab o'tolmaydi.
   Proxied 19.4 da yoqiladi.

3. **SSL/TLS → Overview** → «Custom SSL/TLS» → **Full (strict)**. Standart «Automatic SSL/TLS» ham server sertifikatini
   tekshirib odatda shuni tanlaydi, lekin aniq qo'ygan ma'qul. Server Let's Encrypt sertifikati bilan — bu rejimga mos.
   **Flexible ni tanlamang:** Cloudflare serverga doim oddiy HTTP da ulanadi, server esa HTTPS ga yo'naltiradi —
   sayt cheksiz yo'naltirishga tushib, ochilmay qoladi.
4. **Security → Settings** → «Bot traffic» → **Bot Fight Mode — o'chiq.** U ilovaning API so'rovlarini (fon so'rovlari)
   to'xtatishi mumkin va uni qoida bilan istisno qilib bo'lmaydi. **Under Attack mode — o'chiq.**
5. **SSL/TLS → Edge Certificates → Always Use HTTPS — o'chiq qoldiring.** HTTPS ga yo'naltirishni server o'zi qiladi.
   «Full (strict)» da Cloudflare serverga mijoz kelgan protokolda ulanadi: Let's Encrypt sertifikatini yangilash
   tekshiruvi (`/.well-known/acme-challenge/`, 80-port) serverga oddiy HTTP da yetib boradi.
6. **Rocket Loader — o'chiq** (Speed bo'limi). Sahifaning xavfsizlik siyosati (CSP) begona skriptni to'sadi.

### 19.3 Domen paneli (webspace.uz)

1. DNSSEC yoqilmagan (2026-11-26 da tekshirildi: `.uz` zonasida DS yozuvi yo'q) — bu qadam kerak emas.
2. webspace.uz panelida `libosa.uz` domenining NS (nameserver) sozlamasi: hozirgi to'rttasi (`dns1`–`dns4.webspace.uz`)
   o'rniga Cloudflare bergan ikkitasini yozing (Cloudflare panelida ko'rsatiladi, `….ns.cloudflare.com` ko'rinishida).
3. Kutish: odatda bir necha daqiqa–soat, ko'pi bilan 24 soat. Cloudflare panelida domen «Active» bo'ladi.
   Bu vaqtda sayt avvalgidek ishlaydi — yozuvlar kulrang, eski va yangi DNS ikkalasi ham to'g'ridan-to'g'ri serverga
   olib boradi (bloklangan tarmoqdan esa hali ochilmaydi).
4. Bundan keyin DNS yozuvlari (yangi subdomen va h.k.) faqat Cloudflare panelida o'zgartiriladi — webspace.uz dagi
   yozuvlar endi ishlatilmaydi.

### 19.4 Proxy'ni yoqish

Ikki shart bajarilganda: **Domains** sahifasida `libosa.uz` — «Active», **SSL/TLS → Edge Certificates** da Universal
sertifikat — «Active». Shunda **DNS** bo'limida `libosa.uz`, `www`, `academy` bulutchasini bosib **Proxied** (to'q sariq)
qiling. Shu daqiqadan bloklangan tarmoqlardan ham sayt ochiladi.

### 19.5 Tekshirish

```bash
curl -sI https://libosa.uz/ | grep -i "^server"          # «server: cloudflare» chiqishi kerak
curl -s https://libosa.uz/api/sogliq/                     # {"holat": "ok", ...}
sudo tail -n 5 /var/log/nginx/access.log                  # serverda: mijozlarning haqiqiy IP manzillari (Cloudflare emas)
sudo certbot renew --dry-run                              # sertifikat yangilanishi Cloudflare orqali ishlaydi
```

- Avval bloklangan tarmoqdan (masalan, O'zbektelekom uy interneti) sayt ochilishini tekshiring.
- Ilovaga kirib, bir nechta bo'lim va Telegram botni sinab ko'ring.
- **SSH endi faqat IP bilan:** `ssh root@187.7.77.233` (`libosa.uz` nomi Cloudflare manziliga qaraydi).
  Bloklangan tarmoqdan SSH baribir ochilmaydi — mobil internet yoki boshqa tarmoq kerak.
- Tashqi monitoring (§16) ulangan bo'lsa — `/api/sogliq/` tekshiruvi 200 olayotganini ko'ring.
- Brauzer konsolida `cloudflareinsights` skripti to'silgani (CSP) haqida xato chiqsa — Cloudflare'da Web Analytics'ni
  o'chiring, CSP ni bo'shatmang. Sayt baribir ishlaydi, bu faqat ortiqcha xato.

### 19.6 Orqaga qaytarish

Muammo chiqsa, Cloudflare **DNS** bo'limida `libosa.uz`, `www`, `academy` yozuvlarining bulutchasini bosib
**DNS only** (kulrang) qiling — trafik darhol to'g'ridan-to'g'ri serverga boradi, nameserver'ni qaytarish shart emas.
