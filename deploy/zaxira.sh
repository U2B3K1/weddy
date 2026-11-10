#!/bin/sh
# Libosa zaxira nusxasi: har kuni baza (pg_dump), yakshanba kunlari media (rasmlar) ham.
# Root cron'dan ishga tushiriladi (DEPLOY.md §15): 30 3 * * * root /var/www/libosa/deploy/zaxira.sh
# Baza nusxasi ZAXIRA_KUN kun (standart 14), media nusxasi 4 hafta saqlanadi.
# Baza nusxasi har kuni platforma egasining Telegramiga ham yuboriladi (ega botga ulangan bo'lsa);
# nusxa olinmasa — egaga xato xabari boradi. Sozlama (ixtiyoriy): /etc/libosa-zaxira.conf, masalan
#   ZAXIRA_PAROL='uzun-parol'   — Telegramga ketadigan nusxa shu parol bilan shifrlanadi (tavsiya etiladi)
#   ZAXIRA_TELEGRAM=0           — Telegramga yuborishni o'chirish
# Tiklash: sudo -u postgres pg_restore --clean --if-exists -d libosa /var/backups/libosa/baza-YYYY-MM-DD.dump
# Shifrlangan nusxani ochish: openssl enc -d -aes-256-cbc -pbkdf2 -in baza-YYYY-MM-DD.dump.enc -out baza.dump
set -eu

[ -f /etc/libosa-zaxira.conf ] && . /etc/libosa-zaxira.conf

PAPKA=${ZAXIRA_PAPKA:-/var/backups/libosa}
BAZA=${ZAXIRA_BAZA:-libosa}
KUN=${ZAXIRA_KUN:-14}
ILOVA=${ZAXIRA_ILOVA:-/var/www/libosa}
MEDIA=$ILOVA/backend/media
SANA=$(date +%F)

# Egaga Telegram orqali yuborish. Ilova foydalanuvchisi nomidan ishlaydi (root emas); nusxa fayli unga
# standart kirish orqali beriladi — /var/backups/libosa faqat root uchun ochiq qoladi.
egaga() {
  [ "${ZAXIRA_TELEGRAM:-1}" = 1 ] || return 0
  (cd "$ILOVA/backend" && sudo -u libosa env PYTHONDONTWRITEBYTECODE=1 "$ILOVA/venv/bin/python" manage.py egaga_yuborish "$@") \
    || echo "$(date '+%F %T') egaga yuborib bo'lmadi"
}

# Skript xato bilan tugasa (pg_dump yiqildi, disk to'ldi) — ega shu kuniyoq bilsin
tugadi() {
  kod=$?
  [ "$kod" = 0 ] || egaga --matn "Zaxira nusxa OLINMADI ($SANA, xato kodi $kod). Serverda /var/log/libosa-zaxira.log ni tekshiring." </dev/null || true
}
trap tugadi EXIT

mkdir -p "$PAPKA"
chmod 700 "$PAPKA"  # nusxada mijoz telefonlari va integratsiya kalitlari bor — faqat root o'qiydi

# Avval vaqtinchalik faylga: yarim yozilgan nusxa haqiqiy nusxa o'rnini egallamasin
sudo -u postgres pg_dump -Fc "$BAZA" > "$PAPKA/baza-$SANA.dump.yarim"
mv "$PAPKA/baza-$SANA.dump.yarim" "$PAPKA/baza-$SANA.dump"

if [ "$(date +%u)" = 7 ] && [ -d "$MEDIA" ]; then
  tar -czf "$PAPKA/media-$SANA.tar.gz.yarim" -C "$(dirname "$MEDIA")" media
  mv "$PAPKA/media-$SANA.tar.gz.yarim" "$PAPKA/media-$SANA.tar.gz"
fi

find "$PAPKA" -name 'baza-*.dump' -mtime +"$KUN" -delete
find "$PAPKA" -name 'media-*.tar.gz' -mtime +28 -delete
find "$PAPKA" -name '*.yarim' -mtime +1 -delete

# Server diski buzilsa ham nusxa qolishi uchun boshqa joyga yuborish (rclone sozlangan bo'lsa):
#   rclone copy "$PAPKA" zaxira:libosa --max-age 2d
echo "$(date '+%F %T') zaxira tayyor: baza-$SANA.dump"

# Baza nusxasini egaga yuborish (media yuborilmaydi — u Telegram chegarasidan katta)
HAJM=$(du -h "$PAPKA/baza-$SANA.dump" | cut -f1)
if [ -n "${ZAXIRA_PAROL:-}" ]; then
  export ZAXIRA_PAROL
  openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:ZAXIRA_PAROL -in "$PAPKA/baza-$SANA.dump" \
    | egaga --fayl-nomi "baza-$SANA.dump.enc" --izoh "Zaxira nusxa $SANA ($HAJM), parol bilan shifrlangan"
else
  egaga --fayl-nomi "baza-$SANA.dump" --izoh "Zaxira nusxa $SANA ($HAJM). Shifrlanmagan — bu faylni hech kimga yubormang." \
    < "$PAPKA/baza-$SANA.dump"
fi
