#!/usr/bin/env bash
# Haqiqiy binarlar bilan to'liq smoke test (telefonsiz): mpay-server (TLS) + mpay-tsim.
#   bash scripts/smoke-e2e.sh
# Jarayon ichidagi e2e testlardan farqli o'laroq, bu skript `init` → `serve` → CLI orqali
# foydalanuvchi qiladigan yo'lni aynan takrorlaydi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${MPAY_SMOKE_PORT:-18443}"
WORK="$(mktemp -d)"
SERVER_PID=""
cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

EXE=""
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) EXE=".exe" ;; esac

cargo build -q -p mpay-server -p mpay-terminal-sim
SRV="target/debug/mpay-server$EXE"
TSIM="target/debug/mpay-tsim$EXE"

"$SRV" init --dir "$WORK/sb" --listen "127.0.0.1:$PORT" --tls > "$WORK/init.txt"
"$SRV" serve --config "$WORK/sb/mpay.toml" 2> "$WORK/server.log" &
SERVER_PID=$!

URL="https://localhost:$PORT"
for _ in $(seq 1 50); do
  curl -sf --cacert "$WORK/sb/tls-cert.pem" "$URL/healthz" > /dev/null && break
  sleep 0.2
done

# init yaratgan demo FPAN'lar (konfiguratsiyadan).
mapfile -t PANS < <(grep -E '^pan = ' "$WORK/sb/mpay.toml" | sed -E 's/pan = "([0-9]+)"/\1/')
GREEN="${PANS[0]}"; POOR="${PANS[1]}"; YELLOW="${PANS[2]}"; RED="${PANS[3]}"; OFFLINE="${PANS[4]}"

T() { "$TSIM" --server "$URL" --sandbox "$WORK/sb" --wallet "$WORK/wallet.json" "$@"; }
expect() { # expect <naqsh> <buyruq...>
  local pat="$1"; shift
  local out; out="$("$@" 2>&1)" || true
  echo "$out" | sed 's/^/    /'
  if ! echo "$out" | grep -q -- "$pat"; then echo "XATO: '$pat' kutilgan edi"; exit 1; fi
}

echo "== GREEN provisioning va to'lovlar"
expect "faol" T provision --pan "$GREEN" --expiry 3112
expect "kod 00 (APPROVED).*ARPC: to'g'ri" T tap --amount 12500.00
expect "kod 59 (RISK_DECLINE)" T tap --amount 100 --merchant RISKY000000001
expect "telefonga\|6986" T tap --amount 2000000
expect "kod 00" T tap --amount 2000000 --cdcvm
expect "yangi LUK" T replenish
expect "yaroqli" T status

echo "== 51: mablag' yetarli emas"
expect "faol" T provision --pan "$POOR" --expiry 3112
expect "kod 51 (INSUFFICIENT_FUNDS)" T tap --amount 20000

echo "== YELLOW (OTP) va RED"
expect "faol" T provision --pan "$YELLOW" --expiry 3112
expect "RAD ETILDI: ID&V Red" T provision --pan "$RED" --expiry 3112

echo "== 91: emitent ishlamayapti"
expect "faol" T provision --pan "$OFFLINE" --expiry 3112
expect "kod 91 (ISSUER_OFFLINE)" T tap --amount 100

echo "== Audit zanjiri"
kill "$SERVER_PID"; wait "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
expect "audit zanjiri to'g'ri" "$SRV" audit-verify --config "$WORK/sb/mpay.toml"

echo "== Server logida ochiq PAN yo'q"
for p in "$GREEN" "$POOR" "$YELLOW" "$RED" "$OFFLINE"; do
  if grep -q "$p" "$WORK/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
done
grep -o '"dpan": "[0-9]*"' "$WORK/wallet.json" | sed -E 's/.*"([0-9]+)"/\1/' | while read -r d; do
  if grep -q "$d" "$WORK/server.log"; then echo "XATO: logda ochiq DPAN"; exit 1; fi
done
echo "SMOKE OK"
