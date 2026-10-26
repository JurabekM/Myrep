#!/usr/bin/env bash
# Compose muhiti sirlari (2-faza P2.5): tasodifiy qiymatlar `deploy/secrets/` ga — papka git'ga va
# Docker build kontekstiga tushmaydi. Mavjud fayllar qayta yozilmaydi (`--force` — hammasini yangilash;
# ehtiyot: eski HSM PIN'i bilan yaratilgan token va DB paroli bilan mos kelmay qoladi).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/secrets"
FORCE="${1:-}"
mkdir -p "$DIR"
chmod 700 "$DIR"

put() {   # $1 fayl, $2 qiymat
  local f="$DIR/$1"
  if [ -f "$f" ] && [ "$FORCE" != "--force" ]; then
    return
  fi
  printf '%s' "$2" > "$f"
  # Konteynerdagi `mpay` (uid 10001) o'qiy olsin; papka 700 — host'dagi boshqa foydalanuvchilar uchun yopiq.
  chmod 644 "$f"
  echo "yaratildi: secrets/$1"
}

rand() { openssl rand -hex "$1"; }

put pg_password "$(rand 24)"
put database_url "postgres://mpay:$(cat "$DIR/pg_password")@postgres:5432/mpay"
put hsm_pin "$(rand 8)"
put shield_key "$(rand 24)"
put sms_token "$(rand 24)"
echo "sirlar tayyor: $DIR (qiymatlar chop etilmadi)"
