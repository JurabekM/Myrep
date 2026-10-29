#!/usr/bin/env bash
# Shifrlangan zaxiradan tiklash (P2.5 + 3-faza tayyorgarligi).
#
#   bash deploy/restore.sh <ZAXIRA_PAPKASI> --verify    # alohida bazaga (mpay_restore_check) tiklaydi,
#                                                       # audit xesh-zanjirini tekshiradi; ishlayotgan
#                                                       # muhitga tegmaydi (davriy tiklash mashqi)
#   bash deploy/restore.sh <ZAXIRA_PAPKASI> --replace   # API'larni to'xtatadi, `mpay` bazasini
#                                                       # almashtiradi, qayta ishga tushiradi
#
# Maxfiy kalit: MPAY_BACKUP_IDENTITY (standart: secrets/backup_identity) — oflayn saqlanadigan fayl,
# faqat tiklash paytida olib kelinadi. SHA256SUMS shifrlangan fayllar bo'yicha tekshiriladi; tiklangach
# `mpay-server audit-verify` (zanjir HSM'dagi kalit bilan — DB shu muhit HSM'iga mos bo'lishi shart).
# Muayyan lahzaga tiklash — `pitr-restore.sh`. `state-hsm.tar.gz.age` avtomatik tiklanmaydi.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
SRC="${1:?zaxira papkasi kerak}"
MODE="${2:---verify}"
DC=(docker compose -f "$HERE/docker-compose.yml")
IMG="${MPAY_IMAGE:-mpay-server:local}"
IDENTITY="${MPAY_BACKUP_IDENTITY:-$HERE/secrets/backup_identity}"
export MSYS_NO_PATHCONV=1
[ -f "$IDENTITY" ] || { echo "XATO: maxfiy kalit yo'q: $IDENTITY (MPAY_BACKUP_IDENTITY)" >&2; exit 1; }
# shellcheck source=lib-pg.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib-pg.sh"
PGP="$(pg_primary)"   # joriy yetakchi (ADR-0027)

(cd "$SRC" && sha256sum -c --quiet SHA256SUMS)
echo "== SHA256SUMS to'g'ri"

# Maxfiy kalit konteynerga faqat o'qish uchun ulanadi, ochiq ma'lumot oqimda (diskka yozilmaydi).
dec() {   # $1 (.age) → stdout
  # Kalit fayli 600 (faqat egasi o'qiydi): age konteyneri host foydalanuvchisi uid'i bilan ishlaydi.
  docker run --rm -i --user "$(id -u):$(id -g)" -v "$IDENTITY:/run/backup_identity:ro" --entrypoint age "$IMG" \
    -d -i /run/backup_identity < "$1"
}

case "$MODE" in
  --verify) DB=mpay_restore_check ;;
  --replace) DB=mpay ;;
  *) echo "rejim: --verify yoki --replace" >&2; exit 2 ;;
esac

if [ "$MODE" = --replace ]; then
  echo "== API instansiyalari to'xtatilmoqda"
  "${DC[@]}" stop api-1 api-2
fi

echo "== $DB bazasiga tiklanmoqda"
"${DC[@]}" exec -T "$PGP" sh -c "dropdb -U mpay --if-exists --force $DB && createdb -U mpay $DB"
dec "$SRC/mpay.dump.age" | "${DC[@]}" exec -T "$PGP" pg_restore -U mpay -d "$DB" --no-owner --exit-on-error

echo "== audit xesh-zanjiri ($DB)"
# Parolli URL host'da ko'rinmaydi: konteyner ichida secret'dan, faqat baza nomi almashtiriladi.
"${DC[@]}" run --rm --no-deps -T --entrypoint sh bootstrap -c \
  "MPAY_DATABASE_URL=\"\$(sed 's#/mpay\$#/$DB#' /run/secrets/database_url)\" \
   exec mpay-entrypoint mpay-server audit-verify --config /var/lib/mpay/state/mpay.toml"

if [ "$MODE" = --replace ]; then
  echo "== API instansiyalari ishga tushirilmoqda"
  "${DC[@]}" start api-1 api-2
else
  "${DC[@]}" exec -T "$PGP" dropdb -U mpay "$DB"
fi
echo "tiklash OK ($MODE)"
