#!/bin/sh
# Libosa zaxira nusxasi: har kuni baza (pg_dump), yakshanba kunlari media (rasmlar) ham.
# Root cron'dan ishga tushiriladi (DEPLOY.md §15): 30 3 * * * root /var/www/libosa/deploy/zaxira.sh
# Baza nusxasi ZAXIRA_KUN kun (standart 14), media nusxasi 4 hafta saqlanadi.
# Tiklash: sudo -u postgres pg_restore --clean --if-exists -d libosa /var/backups/libosa/baza-YYYY-MM-DD.dump
set -eu

PAPKA=${ZAXIRA_PAPKA:-/var/backups/libosa}
BAZA=${ZAXIRA_BAZA:-libosa}
KUN=${ZAXIRA_KUN:-14}
MEDIA=/var/www/libosa/backend/media
SANA=$(date +%F)

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
