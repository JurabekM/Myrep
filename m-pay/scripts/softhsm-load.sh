#!/usr/bin/env bash
# 2-faza P2.2: HSM (SoftHSM2, PKCS#11) bilan yuk sinovi — Docker'dagi Linux konteynerda.
# Bir xil konteynerda uch stsenariy solishtiriladi: `memory` KeyStore, SoftHSM 1 sessiya, SoftHSM N sessiya.
#
#   bash scripts/softhsm-load.sh [CARDS] [CONCURRENCY] [SECONDS] [SESSIONS]
#
# MPAY_LOAD_ONLY=memory|hsm — faqat bitta guruh; MPAY_LOAD_SYNC=full|normal — SQLite `synchronous`
# (normal — fsync ta'sirini ajratib ko'rish uchun, production'da emas).
#
# So'rovlar chegarasi o'chiriladi: generator bitta terminal kaliti bilan ishlaydi, kalit chegarasi
# (500/s) production'dagi ko'p terminallarni aks ettirmaydi — server sig'imi o'lchanadi.
# (Konteyner ichidagi skript bitta tirnoqda — u yerda izohlarda apostrof ishlatilmaydi.)
#
# Natijalar: docs/load/p2.2-<stsenariy>.json (repo ichida, target/ emas). Token har safar yangidan,
# PIN tasodifiy va hech qayerga yozilmaydi. Release yig'ish keshi — Docker volume `mpay-softhsm-target`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${MPAY_RUST_IMAGE:-rust:1.97.1-bookworm}"
CARDS="${1:-200}"
CONC="${2:-32}"
SECS="${3:-60}"
SESSIONS="${4:-4}"
mkdir -p "$ROOT/docs/load"

export MSYS_NO_PATHCONV=1

docker run --rm \
  -v "$ROOT:/src:ro" \
  -v "$ROOT/docs/load:/out" \
  -v mpay-cargo-registry:/usr/local/cargo/registry \
  -v mpay-softhsm-target:/target \
  -e CARGO_TARGET_DIR=/target \
  -e CARDS="$CARDS" -e CONC="$CONC" -e SECS="$SECS" -e SESSIONS="$SESSIONS" \
  -e ONLY="${MPAY_LOAD_ONLY:-all}" -e SYNC="${MPAY_LOAD_SYNC:-full}" \
  -w /src \
  "$IMAGE" bash -euo pipefail -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq softhsm2 openssl curl >/dev/null
    echo "CPU: $(nproc) yadro; $(softhsm2-util --version | head -1)"
    cargo build -q --locked --release -p mpay-server --features mpay-server/pkcs11 \
      -p mpay-e2e --bin mpay-server --bin mpay-load
    SRV=/target/release/mpay-server
    LOAD=/target/release/mpay-load

    run() {   # $1 nomi, $2 keystore, $3 sessiyalar
      local name=$1 ks=$2 sess=$3 port=18290 dir=/tmp/sb-$1
      rm -rf /tmp/softhsm "$dir"
      mkdir -p /tmp/softhsm/tokens
      echo "directories.tokendir = /tmp/softhsm/tokens" > /tmp/softhsm/softhsm2.conf
      export SOFTHSM2_CONF=/tmp/softhsm/softhsm2.conf
      export MPAY_PKCS11_PIN="$(openssl rand -hex 8)"
      softhsm2-util --init-token --free --label mpay-load \
        --so-pin "$(openssl rand -hex 8)" --pin "$MPAY_PKCS11_PIN" >/dev/null
      export MPAY_PKCS11_LIB=/usr/lib/softhsm/libsofthsm2.so
      export MPAY_PKCS11_TOKEN_LABEL=mpay-load
      export MPAY_PKCS11_SESSIONS=$sess
      "$SRV" init --dir "$dir" --listen 127.0.0.1:$port --keystore "$ks" >/dev/null
      sed -i "/^path = \"mpay.db\"$/a synchronous = \"$SYNC\"" "$dir/mpay.toml"
      sed -i "/^\[rate_limit\]$/,/^enabled = /s/^enabled = true/enabled = false/" "$dir/mpay.toml"
      local suffix=""
      if [ "$SYNC" != full ]; then suffix="-$SYNC"; fi
      "$LOAD" prepare --dir "$dir" --cards "$CARDS"
      RUST_LOG=warn "$SRV" serve --config "$dir/mpay.toml" 2> "$dir/server.log" &
      local pid=$!
      for _ in $(seq 1 150); do curl -sf http://127.0.0.1:$port/healthz >/dev/null && break; sleep 0.2; done
      echo "== $name (keystore=$ks, sessiyalar=$sess)"
      "$LOAD" run --dir "$dir" --server http://127.0.0.1:$port --cards "$CARDS" \
        --concurrency "$CONC" --duration "$SECS" --out "/out/p2.2-$name$suffix.json"
      kill $pid; wait $pid 2>/dev/null || true
      if grep -qE "99001277[0-9]{8}" "$dir/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
      grep -iE "pkcs11|error" "$dir/server.log" | head -5 || true
    }

    if [ "$ONLY" != hsm ]; then run memory memory 1; fi
    if [ "$ONLY" != memory ]; then
      run hsm-s1 pkcs11 1
      run "hsm-s$SESSIONS" pkcs11 "$SESSIONS"
    fi
    echo "HSM LOAD OK"
  '
