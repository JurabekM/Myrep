#!/usr/bin/env bash
# Yuk sinovi: release `mpay-server` (alohida jarayon, HTTP keep-alive) + `mpay-load`.
#   bash scripts/load-test.sh [CARDS] [CONCURRENCY] [SECONDS] [ENGINE] [SYNC]
# ENGINE: engine (standart, Shield qoidalar + ML) yoki stub.
# SYNC: full (standart, har commit fsync) yoki normal (WAL NORMAL — faqat o'lchov uchun).
# Natija: target/load/report-<ENGINE>-<SYNC>.json va server logi target/load/server.log.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CARDS="${1:-200}"
CONC="${2:-32}"
SECS="${3:-60}"
ENGINE="${4:-engine}"
SYNC="${5:-full}"
PORT="${MPAY_LOAD_PORT:-18190}"
OUT="target/load"
EXE=""
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) EXE=".exe" ;; esac

SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

cargo build -q --release -p mpay-server -p mpay-e2e --bin mpay-server --bin mpay-load
SRV="target/release/mpay-server$EXE"
LOAD="target/release/mpay-load$EXE"

# Natija papkasini o'chirmaymiz (boshqa shell cwd bo'lishi mumkin) — faqat ichini tozalaymiz.
mkdir -p "$OUT"
rm -rf "$OUT/sb" "$OUT"/server.log
"$SRV" init --dir "$OUT/sb" --listen "127.0.0.1:$PORT" > /dev/null
sed -i "s/^engine = \".*\"/engine = \"$ENGINE\"/" "$OUT/sb/mpay.toml"
sed -i "/^path = \"mpay.db\"$/a synchronous = \"$SYNC\"" "$OUT/sb/mpay.toml"
"$LOAD" prepare --dir "$OUT/sb" --cards "$CARDS"

# Server logi: faqat WARN+ (har so'rov INFO logi o'lchovni buzmasin).
RUST_LOG=warn "$SRV" serve --config "$OUT/sb/mpay.toml" 2> "$OUT/server.log" &
SERVER_PID=$!
for _ in $(seq 1 100); do
  curl -sf "http://127.0.0.1:$PORT/healthz" > /dev/null && break
  sleep 0.2
done

"$LOAD" run --dir "$OUT/sb" --server "http://127.0.0.1:$PORT" --cards "$CARDS" \
  --concurrency "$CONC" --duration "$SECS" --out "$OUT/report-$ENGINE-$SYNC.json"

echo "== Server logida ochiq PAN yo'q"
if grep -qE '99001277[0-9]{8}' "$OUT/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
echo "LOAD OK: $OUT/report-$ENGINE-$SYNC.json"
