#!/bin/sh
# Shifrlangan zaxira (ADR-0015): pg_dump (custom format) → age (faqat ochiq kalit; ochish kaliti serverda yo'q) →
# /backups/zanjir-<UTC>.dump.age va .sha256. `ZANJIR_BACKUP_KEEP_DAYS` dan eski fayllar o'chiriladi.
# Ulanish: PGHOST/PGUSER/PGPASSWORD/PGDATABASE (jadvallar egasi — RLS uni cheklamaydi, to'liq nusxa).
set -eu
# busybox ash pipefail'ni qo'llaydi (alpine).
# shellcheck disable=SC3040
set -o pipefail
umask 077
: "${ZANJIR_BACKUP_AGE_RECIPIENT:?}"
dir="${ZANJIR_BACKUP_TARGET:-/backups}"
ts=$(date -u +%Y%m%dT%H%M%SZ)
name="zanjir-${ts}.dump.age"
pg_dump --format=custom --compress=6 | age --encrypt --recipient "$ZANJIR_BACKUP_AGE_RECIPIENT" --output "$dir/$name.partial"
mv "$dir/$name.partial" "$dir/$name"
(cd "$dir" && sha256sum "$name" > "$name.sha256")
find "$dir" -maxdepth 1 -name 'zanjir-*.dump.age*' -type f -mtime +"${ZANJIR_BACKUP_KEEP_DAYS:-30}" -delete
echo "zaxira: $name ($(wc -c < "$dir/$name") bayt)"
