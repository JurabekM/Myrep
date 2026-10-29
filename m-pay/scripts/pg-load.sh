#!/usr/bin/env bash
# 2-faza P2.3: PostgreSQL bilan yuk sinovi — Docker tarmog'ida PostgreSQL konteyneri va server +
# generator konteyneri (softhsm-load.sh bilan bir xil tasvir va release kesh).
#
#   bash scripts/pg-load.sh [CARDS] [CONCURRENCY] [SECONDS] [KEYSTORES]
#
# KEYSTORES: "memory pkcs11" (standart). PostgreSQL standart sozlamada (fsync, synchronous_commit on).
# So'rovlar chegarasi o'chiriladi (generator bitta terminal kaliti bilan ishlaydi). PostgreSQL paroli
# tasodifiy va faqat muhit o'zgaruvchisida. Natijalar: docs/load/p2.3-pg-<keystore>.json.
# (Konteyner ichidagi skript bitta tirnoqda — u yerda izohlarda apostrof ishlatilmaydi.)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${MPAY_RUST_IMAGE:-rust:1.97.1-bookworm}"
PG_IMAGE="${MPAY_PG_IMAGE:-postgres:17-bookworm}"
CARDS="${1:-200}"
CONC="${2:-32}"
SECS="${3:-60}"
KEYSTORES="${4:-memory pkcs11}"
NET=mpay-load-net
PG=mpay-load-pg
mkdir -p "$ROOT/docs/load"
export MSYS_NO_PATHCONV=1

PGPW="$(openssl rand -hex 16)"
cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_USER=mpay -e POSTGRES_PASSWORD="$PGPW" \
  -e POSTGRES_DB=mpay "$PG_IMAGE" -c max_connections=200 >/dev/null
for _ in $(seq 1 60); do docker exec "$PG" pg_isready -U mpay >/dev/null 2>&1 && break; sleep 1; done

docker run --rm --network "$NET" \
  -v "$ROOT:/src:ro" \
  -v "$ROOT/docs/load:/out" \
  -v mpay-cargo-registry:/usr/local/cargo/registry \
  -v mpay-softhsm-target:/target \
  -e CARGO_TARGET_DIR=/target \
  -e CARDS="$CARDS" -e CONC="$CONC" -e SECS="$SECS" -e KEYSTORES="$KEYSTORES" \
  -e PGPW="$PGPW" -e PGHOST="$PG" \
  -w /src \
  "$IMAGE" bash -euo pipefail -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq softhsm2 openssl curl postgresql-client >/dev/null
    echo "CPU: $(nproc) yadro"
    cargo build -q --locked --release -p mpay-server --features mpay-server/pkcs11 \
      -p mpay-e2e --bin mpay-server --bin mpay-load
    SRV=/target/release/mpay-server
    LOAD=/target/release/mpay-load
    run() {
      local ks=$1 port=18390 dir=/tmp/sb-pg-$1 db=mpay_load_$1
      rm -rf "$dir" /tmp/softhsm
      PGPASSWORD="$PGPW" psql -h "$PGHOST" -U mpay -d mpay -qc "DROP DATABASE IF EXISTS $db" -c "CREATE DATABASE $db"
      export MPAY_DATABASE_URL="postgres://mpay:$PGPW@$PGHOST:5432/$db"
      mkdir -p /tmp/softhsm/tokens
      echo "directories.tokendir = /tmp/softhsm/tokens" > /tmp/softhsm/softhsm2.conf
      export SOFTHSM2_CONF=/tmp/softhsm/softhsm2.conf
      export MPAY_PKCS11_PIN="$(openssl rand -hex 8)"
      softhsm2-util --init-token --free --label mpay-load \
        --so-pin "$(openssl rand -hex 8)" --pin "$MPAY_PKCS11_PIN" >/dev/null
      export MPAY_PKCS11_LIB=/usr/lib/softhsm/libsofthsm2.so MPAY_PKCS11_TOKEN_LABEL=mpay-load MPAY_PKCS11_SESSIONS=4
      "$SRV" init --dir "$dir" --listen 127.0.0.1:$port --keystore "$ks" >/dev/null
      sed -i "s|^path = \"mpay.db\"$|url_env = \"MPAY_DATABASE_URL\"|" "$dir/mpay.toml"
      sed -i "/^\[rate_limit\]$/,/^enabled = /s/^enabled = true/enabled = false/" "$dir/mpay.toml"
      grep -q "^url_env" "$dir/mpay.toml"
      "$LOAD" prepare --dir "$dir" --cards "$CARDS"
      RUST_LOG=warn "$SRV" serve --config "$dir/mpay.toml" 2> "$dir/server.log" &
      local pid=$!
      for _ in $(seq 1 150); do curl -sf http://127.0.0.1:$port/healthz >/dev/null && break; sleep 0.2; done
      echo "== PostgreSQL, keystore=$ks"
      "$LOAD" run --dir "$dir" --server http://127.0.0.1:$port --cards "$CARDS" \
        --concurrency "$CONC" --duration "$SECS" --out "/out/p2.3-pg-$ks.json"
      kill $pid; wait $pid 2>/dev/null || true
      if grep -qE "99001277[0-9]{8}" "$dir/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
      if grep -q "$PGPW" "$dir/server.log"; then echo "XATO: logda DB paroli"; exit 1; fi
      grep -iE "error" "$dir/server.log" | head -5 || true
    }
    for ks in $KEYSTORES; do run "$ks"; done
    echo "PG LOAD OK"
  '
