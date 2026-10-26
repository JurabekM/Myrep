#!/usr/bin/env bash
# Muayyan lahzaga tiklash (PITR): asosiy nusxa + WAL arxivi → vaqtinchalik PostgreSQL → tekshiruv.
#
#   bash deploy/pitr-restore.sh <ASOSIY_ZAXIRA> <WAL_ZAXIRA> "<UTC vaqt>" [--keep]
#
#   ASOSIY_ZAXIRA — `backup.sh` papkasi (base.tar.age shu yerdan, maqsad lahzadan OLDIN olingan);
#   WAL_ZAXIRA    — `backup.sh` papkasi (wal.tar.age shu yerdan, maqsad lahzadan KEYIN olingan;
#                   bitta papka ikkalasi uchun ham bo'lishi mumkin);
#   vaqt          — masalan "2026-10-26 12:30:00+00" (PostgreSQL `recovery_target_time`).
#
# Natija: ishlayotgan muhitga tegilmaydi — vaqtinchalik `<loyiha>-pitr` konteynerida tiklanadi,
# audit xesh-zanjiri tekshiriladi, `vault_audit` yozuvlari soni va oxirgi vaqt chiqariladi; so'ng
# konteyner va hajmlar o'chiriladi (`--keep` — qoldiriladi, ma'lumotni qo'lda olish uchun).
# Haqiqiy halokatda: shu natijani `pg_dump` qilib `restore.sh --replace` ga bering.
# Maxfiy kalit: MPAY_BACKUP_IDENTITY (standart: secrets/backup_identity).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
BASE="${1:?asosiy zaxira papkasi kerak}"
WAL="${2:?WAL zaxira papkasi kerak}"
TARGET="${3:?maqsad vaqt kerak (UTC)}"
KEEP="${4:-}"
DC=(docker compose -f "$HERE/docker-compose.yml")
IMG="${MPAY_IMAGE:-mpay-server:local}"
PG_IMG="${MPAY_PG_IMAGE:-postgres:17-alpine}"
IDENTITY="${MPAY_BACKUP_IDENTITY:-$HERE/secrets/backup_identity}"
PROJECT="${COMPOSE_PROJECT_NAME:-mpay}"
NAME="$PROJECT-pitr"
VDATA="$PROJECT-pitr-data"
VWAL="$PROJECT-pitr-wal"
export MSYS_NO_PATHCONV=1
[ -f "$IDENTITY" ] || { echo "XATO: maxfiy kalit yo'q: $IDENTITY" >&2; exit 1; }
for d in "$BASE" "$WAL"; do (cd "$d" && sha256sum -c --quiet SHA256SUMS); done
echo "== SHA256SUMS to'g'ri"

dec() {
  docker run --rm -i -v "$IDENTITY:/run/backup_identity:ro" --entrypoint age "$IMG" \
    -d -i /run/backup_identity < "$1"
}
cleanup() {
  if [ "$KEEP" != --keep ]; then
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker volume rm "$VDATA" "$VWAL" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker volume rm "$VDATA" "$VWAL" >/dev/null 2>&1 || true

echo "== asosiy nusxa va WAL vaqtinchalik hajmlarga"
dec "$BASE/base.tar.age" | docker run --rm -i -v "$VDATA:/d" --entrypoint sh "$PG_IMG" -c \
  'tar -C /d -xf - && chown -R postgres:postgres /d && chmod 700 /d'
dec "$WAL/wal.tar.age" | docker run --rm -i -v "$VWAL:/w" --entrypoint sh "$PG_IMG" -c \
  'tar -C /w -xf - && chown -R postgres:postgres /w'
# Tiklash sozlamalari: WAL arxivdan, maqsad lahzagacha, keyin oddiy rejimga o'tish.
docker run --rm -v "$VDATA:/d" --entrypoint sh "$PG_IMG" -c "
  printf \"restore_command = 'cp /walr/%%f %%p'\nrecovery_target_time = '$TARGET'\nrecovery_target_action = 'promote'\narchive_mode = off\n\" >> /d/postgresql.auto.conf
  touch /d/recovery.signal && chown postgres:postgres /d/recovery.signal /d/postgresql.auto.conf"

echo "== vaqtinchalik PostgreSQL ($NAME) — WAL qayta o'ynalmoqda"
# Tiklanuvchi server sozlamalari asosiydan kam bo'lmasligi shart (max_connections — compose'dagidek).
docker run -d --name "$NAME" --network "${PROJECT}_mpay" -v "$VDATA:/var/lib/postgresql/data" \
  -v "$VWAL:/walr:ro" "$PG_IMG" postgres -c "max_connections=${MPAY_PG_MAX_CONNECTIONS:-200}" > /dev/null
ready=""
for _ in $(seq 1 120); do
  # Tiklash to'xtasa (masalan, sozlama asosiydan kam) — kutmasdan chiqamiz.
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" != true ]; then break; fi
  if [ "$(docker exec "$NAME" psql -U mpay -d mpay -qAtc 'SELECT NOT pg_is_in_recovery()' 2>/dev/null)" = t ]; then
    ready=1; break
  fi
  sleep 1
done
[ -n "$ready" ] || { docker logs --tail 30 "$NAME" >&2; echo "XATO: tiklash tugamadi" >&2; exit 1; }
docker logs "$NAME" 2>&1 | grep -E "recovery stopping|archive recovery complete|consistent recovery state" | sed 's/^/  /'

echo "== audit xesh-zanjiri (tiklangan holat)"
"${DC[@]}" run --rm --no-deps -T --entrypoint sh bootstrap -c \
  "MPAY_DATABASE_URL=\"\$(sed 's#@postgres:#@$NAME:#' /run/secrets/database_url)\" \
   exec mpay-entrypoint mpay-server audit-verify --config /var/lib/mpay/state/mpay.toml" 2>/dev/null
echo "pitr_audit_rows=$(docker exec "$NAME" psql -U mpay -d mpay -qAtc 'SELECT count(*) FROM vault_audit')"
echo "pitr_last_audit_ts=$(docker exec "$NAME" psql -U mpay -d mpay -qAtc 'SELECT max(ts) FROM vault_audit')"
echo "PITR OK ($TARGET)"
