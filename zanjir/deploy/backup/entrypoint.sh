#!/bin/sh
# Zaxira konteyneri (ADR-0015). Standart: har kuni `ZANJIR_BACKUP_AT` (UTC, HH:MM; 21:30 UTC = 02:30 Toshkent) da
# `backup.sh`. Boshqa buyruq berilsa — o'shani bajaradi (`backup.sh`, `restore.sh`, `age-keygen`).
set -eu
if [ "$#" -gt 0 ]; then exec "$@"; fi
: "${ZANJIR_BACKUP_AGE_RECIPIENT:?ochiq kalit (age1...) kerak — maxfiy kalit serverda saqlanmaydi}"
at="${ZANJIR_BACKUP_AT:-21:30}"
echo "zaxira jadvali: har kuni ${at} UTC"
while :; do
  now=$(date -u +%s)
  next=$(date -u -d "$(date -u +%Y-%m-%d) ${at}:00" +%s)
  [ "$next" -le "$now" ] && next=$((next + 86400))
  sleep $((next - now))
  /usr/local/bin/backup.sh || echo "zaxira XATO: $(date -u +%FT%TZ)" >&2
done
