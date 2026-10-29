#!/usr/bin/env bash
# PostgreSQL almashinuvi (ADR-0027): replikani yetakchi qiladi, eski yetakchini to'sib qo'yadi.
#
#   bash deploy/pg-failover.sh            # yetakchi ishlamayapti (yiqilgan) — replika ko'tariladi
#   bash deploy/pg-failover.sh --planned  # rejali (texnik xizmat): yetakchi to'xtatiladi, replika
#                                         # oxirgi WAL'gacha yetib olgach ko'tariladi — yo'qotishsiz
#
# Tartib: 1) to'siq — eski yetakchi konteyneri to'xtatiladi (ikki yetakchi bo'lmasin; qayta ishga tushsa
# ham `pg-node.sh` boshqa yetakchini ko'rib ishga tushmaydi); 2) `pg_promote()`; 3) `pg` proksisi yangi
# yetakchiga o'tganini kutish. Ilovalar qayta ishga tushirilmaydi — ulanishlar proksi orqali.
# Keyin: `bash deploy/pg-rejoin.sh <eski yetakchi>` — uni yangi yetakchining replikasi qilish.
#
# Asinxron replikatsiya: yiqilishda replikaga yetmagan oxirgi tranzaksiyalar yo'qolishi mumkin
# (`mpay_db_replication_lag_bytes`). `TODO(spec):` pilot RPO — sinxron replikatsiya (2 replika) yoki
# avtomatik almashinuv (Patroni + etcd) bank infratuzilmasida.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
DC=(docker compose -f "$HERE/docker-compose.yml")
export MSYS_NO_PATHCONV=1
# shellcheck source=lib-pg.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib-pg.sh"
MODE="${1:-}"

OLD=""
NEW=""
for s in "${PG_NODES[@]}"; do
  case "$(pg_role "$s")" in
    f) OLD="$s" ;;
    t) NEW="$s" ;;
  esac
done
[ -n "$NEW" ] || { echo "XATO: ko'tariladigan replika topilmadi (ishlayotgan va recovery holatida)" >&2; exit 1; }
if [ -z "$OLD" ]; then
  for s in "${PG_NODES[@]}"; do [ "$s" != "$NEW" ] && OLD="$s"; done
fi

if [ "$MODE" = --planned ]; then
  [ "$(pg_role "$OLD")" = f ] || { echo "XATO: --planned uchun yetakchi ishlab turishi kerak" >&2; exit 1; }
  echo "== rejali almashinuv: $OLD → $NEW"
  lsn="$("${DC[@]}" exec -T "$OLD" psql -U mpay -d mpay -qAtc "SELECT pg_current_wal_lsn()" | tr -d '\r')"
  # Yangi yozuvlar to'xtaydi (fast shutdown: walsender oxirgi WAL'ni replikaga yuboradi).
  "${DC[@]}" stop "$OLD" >/dev/null
  caught=""
  for _ in $(seq 1 30); do
    d="$("${DC[@]}" exec -T "$NEW" psql -U mpay -d mpay -qAtc \
      "SELECT pg_wal_lsn_diff(pg_last_wal_replay_lsn(), '$lsn') >= 0" | tr -d '\r')"
    [ "$d" = t ] && { caught=1; break; }
    sleep 1
  done
  [ -n "$caught" ] || { echo "XATO: replika $lsn gacha yetib olmadi — $OLD qayta ishga tushiring" >&2; exit 1; }
  echo "   replika $lsn gacha yetib oldi"
else
  [ "$(pg_role "$OLD")" != f ] || {
    echo "XATO: $OLD hali yetakchi va ishlayapti — rejali almashinuv uchun --planned" >&2; exit 1; }
  echo "== almashinuv (yetakchi $OLD javob bermayapti) → $NEW"
  echo "   to'siq: $OLD to'xtatilmoqda"
  "${DC[@]}" stop "$OLD" >/dev/null 2>&1 || true
fi

echo "== $NEW ko'tarilmoqda (pg_promote)"
"${DC[@]}" exec -T "$NEW" psql -U mpay -d mpay -qAtc "SELECT pg_promote(true, 60)" | tr -d '\r' | grep -qx t
ok=""
for _ in $(seq 1 30); do
  if "${DC[@]}" exec -T pg pg-primary-check - - 127.0.0.1 5432; then ok=1; break; fi
  sleep 1
done
[ -n "$ok" ] || { echo "XATO: pg proksisi yangi yetakchini ko'rmadi" >&2; exit 1; }
# Checkpoint'dan keyin nazorat faylida yangi timeline ko'rinadi.
"${DC[@]}" exec -T "$NEW" psql -U mpay -d mpay -qAtc "CHECKPOINT" >/dev/null
tl="$("${DC[@]}" exec -T "$NEW" psql -U mpay -d mpay -qAtc "SELECT timeline_id FROM pg_control_checkpoint()" | tr -d '\r')"
echo "almashinuv tayyor: yetakchi $NEW (timeline $tl); keyingi qadam: bash deploy/pg-rejoin.sh $OLD"
