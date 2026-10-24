#!/usr/bin/env bash
# Haqiqiy binarlar bilan to'liq smoke test (telefonsiz): mpay-server (TLS, Shield dvigateli) + mpay-tsim.
#   bash scripts/smoke-e2e.sh
# Jarayon ichidagi e2e testlardan farqli o'laroq, bu skript `init` → `serve` → CLI orqali
# foydalanuvchi qiladigan yo'lni aynan takrorlaydi. Har "telefon" — alohida hamyon fayli (qurilma).
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
for _ in $(seq 1 100); do
  curl -sf --cacert "$WORK/sb/tls-cert.pem" "$URL/healthz" > /dev/null && break
  sleep 0.2
done

# init yaratgan demo FPAN'lar (konfiguratsiyadan).
mapfile -t PANS < <(grep -E '^pan = ' "$WORK/sb/mpay.toml" | sed -E 's/pan = "([0-9]+)"/\1/')
GREEN="${PANS[0]}"; POOR="${PANS[1]}"; OFFLINE="${PANS[4]}"

# T <telefon> <buyruq...> — har telefon o'z hamyon faylida (alohida qurilma kaliti).
T() { local phone="$1"; shift; "$TSIM" --server "$URL" --sandbox "$WORK/sb" --wallet "$WORK/$phone.json" "$@"; }
expect() { # expect <naqsh> <buyruq...>
  local pat="$1"; shift
  local out; out="$("$@" 2>&1)" || true
  echo "$out" | sed 's/^/    /'
  if ! echo "$out" | grep -q -- "$pat"; then echo "XATO: '$pat' kutilgan edi"; exit 1; fi
}
luhn_pan() { # 15 raqamli prefiksga Luhn raqamini qo'shadi
  python -c "import sys
p=sys.argv[1]; s=0
for i,ch in enumerate(reversed(p)):
    d=int(ch)
    if i%2==0:
        d*=2
        d-=9 if d>9 else 0
    s+=d
print(p+str((10-s%10)%10))" "$1"
}

echo "== GREEN provisioning va to'lovlar (telefon A)"
expect "faol" T A provision --pan "$GREEN" --expiry 3112
expect "kod 00 (APPROVED).*ARPC: to'g'ri" T A tap --amount 12500.00
expect "6986" T A tap --amount 2000000
expect "kod 00" T A tap --amount 2000000 --cdcvm
expect "yangi LUK" T A replenish
expect "yaroqli" T A status

echo "== 59: karta testlash namunasi — kichik onlayn summalar (Shield DECLINE)"
found=""
for _ in $(seq 1 9); do
  out="$(T A tap --amount 500 --merchant WEB0000000003 2>&1 || true)"
  echo "$out" | sed 's/^/    /'
  if echo "$out" | grep -q "kod 59 (RISK_DECLINE)"; then found=1; break; fi
done
[ -n "$found" ] || { echo "XATO: 59 kutilgan edi"; exit 1; }

echo "== 51: mablag' yetarli emas (telefon B)"
expect "faol" T B provision --pan "$POOR" --expiry 3112
expect "kod 51 (INSUFFICIENT_FUNDS)" T B tap --amount 20000

echo "== YELLOW: o'sha kartani ikkinchi telefonga qo'shish (step-up OTP)"
expect "OTP talab qilinadi" T C provision --pan "$GREEN" --expiry 3112

echo "== RED: qurilma fermasi (bitta telefonda 6 karta)"
for i in 1 2 3 4 5; do
  T D provision --pan "$(luhn_pan "99001210000$(printf '%04d' $((5000 + i)))")" --expiry 3112 > /dev/null 2>&1 || true
done
expect "RAD ETILDI: ID&V Red.*IDV_DEVICE_FARM" T D provision --pan "$(luhn_pan 990012100005006)" --expiry 3112

echo "== 91: emitent ishlamayapti (telefon E)"
expect "faol" T E provision --pan "$OFFLINE" --expiry 3112
expect "kod 91 (ISSUER_OFFLINE)" T E tap --amount 100

echo "== Audit zanjiri"
kill "$SERVER_PID"; wait "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
expect "audit zanjiri to'g'ri" "$SRV" audit-verify --config "$WORK/sb/mpay.toml"

echo "== Server logida ochiq PAN/DPAN yo'q"
for p in "${PANS[@]}"; do
  if grep -q "$p" "$WORK/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
done
cat "$WORK"/*.json | grep -o '"dpan": "[0-9]*"' | sed -E 's/.*"([0-9]+)"/\1/' | while read -r d; do
  if grep -q "$d" "$WORK/server.log"; then echo "XATO: logda ochiq DPAN"; exit 1; fi
done
echo "SMOKE OK"
