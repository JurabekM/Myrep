#!/usr/bin/env bash
# Zaxiradan tiklash (2-faza P2.5, ADR-0020).
#
#   bash deploy/restore.sh <ZAXIRA_PAPKASI> --verify    # alohida bazaga (mpay_restore_check) tiklaydi,
#                                                       # audit xesh-zanjirini tekshiradi; ishlayotgan
#                                                       # muhitga tegmaydi (davriy tiklash mashqi)
#   bash deploy/restore.sh <ZAXIRA_PAPKASI> --replace   # API'larni to'xtatadi, `mpay` bazasini
#                                                       # almashtiradi, qayta ishga tushiradi
#
# Ikkala holatda ham SHA256SUMS tekshiriladi va tiklangandan keyin `mpay-server audit-verify` ishlaydi
# (zanjir HSM'dagi kalit bilan tekshiriladi — tiklangan DB shu muhit HSM'iga mos bo'lishi shart).
# `state-hsm.tar.gz` avtomatik tiklanmaydi: HSM/holat yo'qolgan bo'lsa, uni bo'sh hajmlarga qo'lda oching.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
SRC="${1:?zaxira papkasi kerak}"
MODE="${2:---verify}"
DC=(docker compose -f "$HERE/docker-compose.yml")
export MSYS_NO_PATHCONV=1

(cd "$SRC" && sha256sum -c --quiet SHA256SUMS)
echo "== SHA256SUMS to'g'ri"

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
"${DC[@]}" exec -T postgres sh -c "dropdb -U mpay --if-exists --force $DB && createdb -U mpay $DB"
"${DC[@]}" exec -T postgres pg_restore -U mpay -d "$DB" --no-owner --exit-on-error < "$SRC/mpay.dump"

echo "== audit xesh-zanjiri ($DB)"
# Parolli URL host'da ko'rinmaydi: konteyner ichida secret'dan, faqat baza nomi almashtiriladi.
"${DC[@]}" run --rm --no-deps -T --entrypoint sh bootstrap -c \
  "MPAY_DATABASE_URL=\"\$(sed 's#/mpay\$#/$DB#' /run/secrets/database_url)\" \
   exec mpay-entrypoint mpay-server audit-verify --config /var/lib/mpay/state/mpay.toml"

if [ "$MODE" = --replace ]; then
  echo "== API instansiyalari ishga tushirilmoqda"
  "${DC[@]}" start api-1 api-2
else
  "${DC[@]}" exec -T postgres dropdb -U mpay "$DB"
fi
echo "tiklash OK ($MODE)"
