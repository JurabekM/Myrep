#!/bin/sh
# Zaxiradan tiklash (ADR-0015, RUNBOOK): restore.sh <fayl.dump.age> <age maxfiy kaliti fayli>
# Faqat BO'SH bazaga (PGDATABASE) tiklaydi — mavjud ma'lumot ustiga yozmaydi. Hash fayli bo'lsa — avval tekshiriladi.
set -eu
# busybox ash pipefail'ni qo'llaydi (alpine).
# shellcheck disable=SC3040
set -o pipefail
file="${1:?zaxira fayli}"
identity="${2:?age maxfiy kaliti fayli}"
if [ -f "$file.sha256" ]; then
  (cd "$(dirname "$file")" && sha256sum -c "$(basename "$file").sha256" >/dev/null) || { echo "hash mos emas: $file" >&2; exit 2; }
fi
tables=$(psql -tAc "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
if [ "$tables" != "0" ]; then
  echo "baza bo'sh emas ($tables jadval) — tiklash faqat yangi bazaga (RUNBOOK)" >&2
  exit 3
fi
age --decrypt --identity "$identity" "$file" | pg_restore --exit-on-error --single-transaction --dbname "$PGDATABASE"
echo "tiklandi: $(basename "$file")"
