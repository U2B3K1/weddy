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
sudo -u libosa git clone https://github.com/U2B3K1/weddy.git libosa
# agar repo allaqachon yaratilgan bo'lsa:
#   sudo rm -rf libosa && sudo -u libosa git clone https://github.com/U2B3K1/weddy.git libosa
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
sudo -u libosa venv/bin/pip install -r backend/requirements.txt && \
cd backend && sudo -u libosa ../venv/bin/python manage.py migrate && \
sudo -u libosa ../venv/bin/python manage.py collectstatic --noinput && \
cd ../frontend && sudo -u libosa npm install && sudo -u libosa npm run build && \
sudo systemctl restart libosa.service libosa-telegram.service
```

---

## 15. Zaxira (backup)

PostgreSQL dump (kunlik cron qilib qo'yish mumkin):

```bash
sudo -u postgres pg_dump libosa | gzip > /var/backups/libosa-$(date +%F).sql.gz
```

Media papkasini ham nusxalang: `/var/www/libosa/backend/media/`.

---

## 16. Muhim eslatmalar

1. **`.env` hech qachon gitga kirmaydi.** `.env.example` bilan ishlang.
2. `DEBUG=False` productionda shart. Bu `settings.py` dagi HTTPS xavfsizlik blokini ham
   faollashtiradi (xavfsiz cookie + CSRF).
3. `ALLOWED_HOSTS` ga faqat haqiqiy domenlar yozing — `*` productionda xavfli.
4. Bot tokeni API javoblarida va loglarda **chiqmasligi kerak** — kod shuni ta'minlaydi.
5. Frontend `VITE_API_URL=/api` bo'lgani uchun port 8000 tashqariga ochilmaydi — faqat nginx.
