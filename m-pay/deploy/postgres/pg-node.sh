#!/bin/sh
# PostgreSQL tuguni (ADR-0027): bir xil skript ikki xizmatda (`postgres`, `postgres-replica`).
#
# * Ma'lumot papkasi bo'sh:
#   - `PG_BOOTSTRAP=primary` va boshqa tugunlarda yetakchi yo'q — birinchi ishga tushish: initdb
#     (`docker-entrypoint.sh`), replikatsiya roli `initdb.d/` skriptida;
#   - aks holda — joriy yetakchidan `pg_basebackup` (replika: `standby.signal`, `primary_conninfo`,
#     replikatsiya sloti). Almashinuvdan keyin eski yetakchini qayta qo'shish ham shu yo'l
#     (`deploy/pg-rejoin.sh` papkani tozalaydi).
# * Papka bor va tugun yetakchi bo'lib ishga tushishi kerak (`standby.signal` yo'q), lekin boshqa tugun
#   allaqachon yetakchi — **ishga tushmaydi** (to'siq): almashinuvdan keyin qaytgan eski yetakchi ikkinchi
#   yetakchi bo'lmasin.
#
# Muhit: PG_PEERS (boshqa tugunlar), PG_SLOT (shu tugunning replikatsiya sloti), PG_BOOTSTRAP.
# Sir: /run/secrets/pg_repl_password (`replicator` roli).
set -eu

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
REPL_PW_FILE=/run/secrets/pg_repl_password
PEERS="${PG_PEERS:-}"
SLOT="${PG_SLOT:?PG_SLOT kerak}"

mkdir -p /wal && chown postgres:postgres /wal

is_primary() {   # $1 xost → 0, agar u yozish uchun ochiq yetakchi bo'lsa
  r="$(PGPASSWORD="$(cat "$REPL_PW_FILE")" PGCONNECT_TIMEOUT=2 \
    psql -h "$1" -U replicator -d mpay -qAtc "SELECT pg_is_in_recovery()" 2>/dev/null || true)"
  [ "$r" = f ]
}

find_primary() {
  for p in $PEERS; do
    if is_primary "$p"; then echo "$p"; return 0; fi
  done
  return 1
}

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  if [ "${PG_BOOTSTRAP:-}" = primary ] && ! find_primary >/dev/null; then
    echo "pg-node: birinchi ishga tushish — yangi klaster (yetakchi)"
  else
    echo "pg-node: yetakchi kutilmoqda (replika nusxasi uchun)"
    primary=""
    for _ in $(seq 1 120); do
      primary="$(find_primary || true)"
      [ -n "$primary" ] && break
      sleep 1
    done
    [ -n "$primary" ] || { echo "pg-node: XATO — yetakchi topilmadi" >&2; exit 1; }
    export PGPASSWORD="$(cat "$REPL_PW_FILE")"
    # Eski (shu nomdagi) slot qolgan bo'lsa — o'chiriladi, yangisi nusxa bilan birga yaratiladi.
    psql -h "$primary" -U replicator -d mpay -qAtc \
      "SELECT pg_drop_replication_slot('$SLOT') FROM pg_replication_slots WHERE slot_name = '$SLOT'" >/dev/null
    mkdir -p "$PGDATA"
    pg_basebackup -h "$primary" -U replicator -D "$PGDATA" -R -X stream -C -S "$SLOT" --checkpoint=fast
    unset PGPASSWORD
    chown -R postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
    echo "pg-node: replika tayyor ($primary dan nusxa, slot $SLOT)"
  fi
elif [ ! -f "$PGDATA/standby.signal" ]; then
  if other="$(find_primary)"; then
    echo "pg-node: TO'SIQ — $other allaqachon yetakchi; bu tugun yetakchi bo'lib ishga tushmaydi." >&2
    echo "         Qayta qo'shish: bash deploy/pg-rejoin.sh <xizmat>" >&2
    exit 1
  fi
fi

exec docker-entrypoint.sh postgres \
  -c max_connections="${PG_MAX_CONNECTIONS:-200}" \
  -c wal_level=replica -c archive_mode=on -c archive_timeout=300 \
  -c "archive_command=test ! -f /wal/%f && cp %p /wal/%f" \
  -c max_wal_senders=10 -c max_replication_slots=10 -c hot_standby=on \
  -c wal_keep_size=256MB -c max_slot_wal_keep_size=2GB
