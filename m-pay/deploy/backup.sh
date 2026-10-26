#!/usr/bin/env bash
# Shifrlangan zaxira nusxa (P2.5 + 3-faza tayyorgarligi): ishlab turgan compose muhitidan, to'xtatmasdan.
#
#   bash deploy/backup.sh [CHIQISH_PAPKASI]      # standart: deploy/backups/<UTC vaqt>/
#
# Tarkib (har biri `age` bilan shifrlangan, ochiq kalit — secrets/backup_recipient, `backup-keygen.sh`):
#   mpay.dump.age        — `pg_dump -Fc`: bitta izchil snapshot (oddiy tiklash, `restore.sh`).
#   base.tar.age         — `pg_basebackup` (tar, kerakli WAL bilan): PITR boshlang'ich nuqtasi.
#   wal.tar.age          — WAL arxivi (`archive_command`): asosiy nusxadan keyingi har lahzaga tiklash
#                          (`pitr-restore.sh`).
#   state-hsm.tar.gz.age — konfiguratsiya holati va SoftHSM tokeni.
#   SHA256SUMS, MANIFEST — shifrlangan fayllar nazorati va vaqt.
#
# Ochiq ma'lumot diskka tushmaydi: oqim konteyner ichida shifrlanadi. Maxfiy kalit serverda bo'lmasa,
# server buzilganda ham zaxiralar o'qilmaydi. Karta ma'lumoti DB'da baribir KEK/DEK bilan shifrlangan.
# TODO(spec): zaxirani boshqa joyga (offsite) yuborish, saqlash muddati, bank HSM'ining o'z zaxira tartibi.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-$HERE/backups}/$TS"
DC=(docker compose -f "$HERE/docker-compose.yml")
IMG="${MPAY_IMAGE:-mpay-server:local}"
export MSYS_NO_PATHCONV=1
REC="$HERE/secrets/backup_recipient"
[ -f "$REC" ] || { echo "XATO: $REC yo'q — avval: bash deploy/backup-keygen.sh" >&2; exit 1; }
RECIPIENT="$(cat "$REC")"
mkdir -p "$OUT"

enc() {   # stdin → age (ochiq kalit) → $1
  docker run --rm -i --entrypoint age "$IMG" -r "$RECIPIENT" > "$1"
}

echo "== PostgreSQL dump → mpay.dump.age"
"${DC[@]}" exec -T postgres pg_dump -U mpay -d mpay -Fc | enc "$OUT/mpay.dump.age"

echo "== asosiy nusxa (pg_basebackup) → base.tar.age"
"${DC[@]}" exec -T postgres pg_basebackup -U mpay -D - -Ft -X fetch --checkpoint=fast | enc "$OUT/base.tar.age"

echo "== WAL arxivi → wal.tar.age"
# Joriy segment ham arxivga tushsin (oxirgi tranzaksiyalargacha tiklash uchun).
# Avval kichik WAL yozuvi: oxirgi almashtirishdan beri yozuv bo'lmasa `pg_switch_wal()` hech narsa
# qilmaydi va joriy (arxivlanmagan) segmentni ko'rsatadi. Yopilgan segment — `switch_lsn - 1` niki.
"${DC[@]}" exec -T postgres psql -U mpay -d mpay -qAtc \
  "SELECT pg_logical_emit_message(false, 'mpay-backup', now()::text)" > /dev/null
seg="$("${DC[@]}" exec -T postgres psql -U mpay -d mpay -qAtc "SELECT pg_walfile_name(pg_switch_wal() - 1)" | tr -d '\r')"
archived=""
for _ in $(seq 1 40); do
  if "${DC[@]}" exec -T postgres test -f "/wal/$seg"; then archived=1; break; fi
  sleep 0.5
done
[ -n "$archived" ] || { echo "XATO: WAL segmenti $seg arxivlanmadi (archive_command?)" >&2; exit 1; }
"${DC[@]}" exec -T postgres tar -C /wal -cf - . | enc "$OUT/wal.tar.age"

echo "== holat va HSM tokeni → state-hsm.tar.gz.age"
"${DC[@]}" run --rm --no-deps -T --entrypoint tar bootstrap \
  -C /var/lib/mpay -czf - state hsm | enc "$OUT/state-hsm.tar.gz.age"

printf 'created_utc=%s\nrecipient=%s\n' "$TS" "$RECIPIENT" > "$OUT/MANIFEST"
(cd "$OUT" && sha256sum mpay.dump.age base.tar.age wal.tar.age state-hsm.tar.gz.age MANIFEST > SHA256SUMS)
echo "zaxira tayyor (shifrlangan): $OUT"
du -h "$OUT"/*.age | sed 's/^/  /'
