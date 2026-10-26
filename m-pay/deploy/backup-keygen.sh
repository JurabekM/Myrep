#!/usr/bin/env bash
# Zaxira shifrlash kalitlari (age, X25519): bir marta, zaxira olishdan oldin.
#
#   bash deploy/backup-keygen.sh
#
# * secrets/backup_recipient — ochiq kalit (`age1…`): serverda qoladi, `backup.sh` shu bilan shifrlaydi.
# * secrets/backup_identity  — MAXFIY kalit: tiklash uchun. Uni **oflayn** saqlang (seyf, HSM, qog'oz
#   nusxa) va serverdan o'chiring — server buzilsa ham zaxiralar o'qilmasin. Sandbox/sinovda qoladi.
# Mavjud kalitlar qayta yozilmaydi (yo'qolgan identity bilan eski zaxiralarni ochib bo'lmaydi).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/secrets"
IMG="${MPAY_IMAGE:-mpay-server:local}"
mkdir -p "$DIR"
chmod 700 "$DIR"
if [ -f "$DIR/backup_recipient" ]; then
  echo "kalitlar mavjud: secrets/backup_recipient ($(cut -c1-12 "$DIR/backup_recipient")…)"
  exit 0
fi
key="$(docker run --rm --entrypoint age-keygen "$IMG" 2>/dev/null)"
printf '%s\n' "$key" | sed -n 's/^# public key: //p' > "$DIR/backup_recipient"
printf '%s\n' "$key" | grep '^AGE-SECRET-KEY-' > "$DIR/backup_identity"
unset key
chmod 644 "$DIR/backup_recipient"
chmod 600 "$DIR/backup_identity"
grep -q '^age1' "$DIR/backup_recipient" || { echo "XATO: ochiq kalit yaratilmadi" >&2; exit 1; }
echo "yaratildi: secrets/backup_recipient ($(cut -c1-12 "$DIR/backup_recipient")…)"
echo "yaratildi: secrets/backup_identity — MAXFIY: oflayn saqlang va serverdan o'chiring (tiklashda kerak)"
