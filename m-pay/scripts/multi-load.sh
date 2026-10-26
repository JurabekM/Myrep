#!/usr/bin/env bash
# 2-faza P2.4: ko'p instansiya yuk sinovi — PostgreSQL + Shield roli + N ta API instansiyasi,
# generator so'rovlarni instansiyalar orasida round-robin taqsimlaydi (load balancer simulyatsiyasi;
# handshake ham ikki instansiyaga bo'linadi). Taqqoslash: 1 instansiya, mahalliy Shield.
#
#   bash scripts/multi-load.sh [CARDS] [CONCURRENCY] [SECONDS] [INSTANCES]
#
# Natijalar: docs/load/p2.4-*.json. PostgreSQL paroli va Shield kaliti tasodifiy, faqat muhitda.
# (Konteyner ichidagi skript bitta tirnoqda — u yerda izohlarda apostrof ishlatilmaydi.)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${MPAY_RUST_IMAGE:-rust:1.97.1-bookworm}"
PG_IMAGE="${MPAY_PG_IMAGE:-postgres:17-bookworm}"
CARDS="${1:-200}"
CONC="${2:-32}"
SECS="${3:-60}"
INSTANCES="${4:-2}"
NET=mpay-multi-net
PG=mpay-multi-pg
mkdir -p "$ROOT/docs/load"
export MSYS_NO_PATHCONV=1

PGPW="$(openssl rand -hex 16)"
cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_USER=mpay -e POSTGRES_PASSWORD="$PGPW" \
  -e POSTGRES_DB=mpay "$PG_IMAGE" -c max_connections=300 >/dev/null
for _ in $(seq 1 60); do docker exec "$PG" pg_isready -U mpay >/dev/null 2>&1 && break; sleep 1; done

docker run --rm --network "$NET" \
  -v "$ROOT:/src:ro" \
  -v "$ROOT/docs/load:/out" \
  -v mpay-cargo-registry:/usr/local/cargo/registry \
  -v mpay-softhsm-target:/target \
  -e CARGO_TARGET_DIR=/target \
  -e CARDS="$CARDS" -e CONC="$CONC" -e SECS="$SECS" -e INSTANCES="$INSTANCES" \
  -e PGPW="$PGPW" -e PGHOST="$PG" \
  -w /src \
  "$IMAGE" bash -euo pipefail -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq openssl curl postgresql-client >/dev/null
    echo "CPU: $(nproc) yadro"
    cargo build -q --locked --release -p mpay-server -p mpay-e2e --bin mpay-server --bin mpay-load
    SRV=/target/release/mpay-server
    LOAD=/target/release/mpay-load
    PIDS=""
    stop_all() { for p in $PIDS; do kill $p 2>/dev/null || true; wait $p 2>/dev/null || true; done; PIDS=""; }
    trap stop_all EXIT
    wait_up() { for _ in $(seq 1 150); do curl -sf "$1/healthz" >/dev/null && return 0; sleep 0.2; done; echo "XATO: $1 ishga tushmadi"; exit 1; }

    prepare() {   # $1 nomi
      local name=$1 dir=/tmp/sb-$1 db=mpay_multi_$1
      rm -rf "$dir"
      PGPASSWORD="$PGPW" psql -h "$PGHOST" -U mpay -d mpay -qc "DROP DATABASE IF EXISTS $db" -c "CREATE DATABASE $db"
      export MPAY_DATABASE_URL="postgres://mpay:$PGPW@$PGHOST:5432/$db"
      "$SRV" init --dir "$dir" --listen 127.0.0.1:18400 >/dev/null
      sed -i "s|^path = \"mpay.db\"$|url_env = \"MPAY_DATABASE_URL\"|" "$dir/mpay.toml"
      sed -i "/^\[rate_limit\]$/,/^enabled = /s/^enabled = true/enabled = false/" "$dir/mpay.toml"
      "$LOAD" prepare --dir "$dir" --cards "$CARDS"
    }

    run_load() {   # $1 nomi, $2 serverlar
      echo "== $1"
      "$LOAD" run --dir "/tmp/sb-$3" --server "$2" --cards "$CARDS" \
        --concurrency "$CONC" --duration "$SECS" --out "/out/p2.4-$1.json"
    }

    # 1) Bitta instansiya, mahalliy Shield (taqqoslash).
    prepare single
    RUST_LOG=warn "$SRV" serve --config /tmp/sb-single/mpay.toml 2> /tmp/sb-single/server.log &
    PIDS="$!"; wait_up http://127.0.0.1:18400
    run_load "1-instansiya" "http://127.0.0.1:18400" single
    stop_all

    # 2) Shield roli + N ta API instansiyasi, bitta konfiguratsiya va bitta PostgreSQL.
    prepare multi
    D=/tmp/sb-multi
    export MPAY_SHIELD_KEY="$(openssl rand -hex 24)"
    H=$(printf "%s" "$MPAY_SHIELD_KEY" | sha256sum | cut -d" " -f1)
    printf "\n[[auth.keys]]\nid = \"api-shield\"\nrole = \"shield\"\nsha256 = \"%s\"\n" "$H" >> $D/mpay.toml
    sed "s|^listen = .*|listen = \"127.0.0.1:18500\"|" $D/mpay.toml > $D/shield.toml
    RUST_LOG=warn "$SRV" shield --config $D/shield.toml 2> $D/shield.log &
    PIDS="$PIDS $!"; wait_up http://127.0.0.1:18500
    sed -i "/^engine = \"engine\"$/a mode = \"remote\"" $D/mpay.toml
    printf "\n[shield.remote]\nurl = \"http://127.0.0.1:18500\"\nkey_env = \"MPAY_SHIELD_KEY\"\ntimeout_ms = 500\n" >> $D/mpay.toml
    SERVERS=""
    for i in $(seq 1 "$INSTANCES"); do
      port=$((18400 + i))
      sed "s|^listen = .*|listen = \"127.0.0.1:$port\"|" $D/mpay.toml > $D/api-$i.toml
      RUST_LOG=warn "$SRV" serve --config $D/api-$i.toml 2> $D/api-$i.log &
      PIDS="$PIDS $!"; wait_up http://127.0.0.1:$port
      SERVERS="$SERVERS${SERVERS:+,}http://127.0.0.1:$port"
    done
    run_load "$INSTANCES-instansiya-shield-roli" "$SERVERS" multi
    curl -s http://127.0.0.1:18500/healthz; echo
    stop_all
    for f in /tmp/sb-single/server.log $D/shield.log $D/api-*.log; do
      if grep -qE "99001277[0-9]{8}" "$f"; then echo "XATO: $f logida ochiq PAN"; exit 1; fi
      if grep -q "$PGPW" "$f" || grep -q "$MPAY_SHIELD_KEY" "$f"; then echo "XATO: $f logida sir"; exit 1; fi
    done
    echo "== zaxira rejimi (SHIELD_DEGRADED) loglarda:"; grep -c "Shield roli javob bermadi" $D/api-*.log || true
    echo "MULTI LOAD OK"
  '
