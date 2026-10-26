#!/usr/bin/env bash
# 10 daqiqalik bank namoyishi (docs/demo-script.md): haqiqiy binarlar, TLS, Shield dvigateli.
#   bash scripts/demo.sh            — interaktiv: har qadamdan oldin Enter kutadi
#   DEMO_AUTO=1 bash scripts/demo.sh — avtomatik: har natija tekshiriladi (CI / repetitsiya)
# Har "telefon" — alohida soft-wallet fayli (alohida qurilma kaliti va attestatsiya).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${MPAY_DEMO_PORT:-18443}"
DEMO="${MPAY_DEMO_DIR:-$ROOT/target/demo}"
AUTO="${DEMO_AUTO:-0}"
EXE=""
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) EXE=".exe" ;; esac
# Windows'da `python3` — Store "stub" bo'lishi mumkin, shuning uchun avval `python`.
PY="$(command -v python || command -v python3)"

SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

B=$'\e[1m'; G=$'\e[32m'; C=$'\e[36m'; R=$'\e[0m'
step() { echo; echo "${B}${G}━━ $* ━━${R}"; }
say() { echo "${C}» $*${R}"; }
pause() { if [ "$AUTO" != "1" ]; then read -r -p "  [Enter] " _ < /dev/tty; fi; }
# show <naqsh> <buyruq...> — buyruqni ko'rsatadi, bajaradi, natijada naqsh bo'lishini tekshiradi.
show() {
  local pat="$1"; shift
  echo "${B}\$ ${*/#$ROOT\//}${R}"
  local out; out="$("$@" 2>&1)" || true
  echo "$out" | sed 's/^/    /'
  if ! echo "$out" | grep -q -- "$pat"; then echo "XATO: '$pat' kutilgan edi"; exit 1; fi
}

# Ko'rgazmali yordamchilar (ekranda nomi bilan ko'rinadi).
db_scan_pans() { # SQLite fayllarida (asosiy + WAL) test FPAN'larning ochiq ko'rinishini qidiradi
  "$PY" - "$DEMO/sb" "${PANS[@]}" <<'EOF'
import sys, glob
raw = b"".join(open(f, "rb").read() for f in glob.glob(sys.argv[1] + "/mpay.db*"))
hits = [p for p in sys.argv[2:] if p.encode() in raw]
print("ochiq PAN topildi: %d" % len(hits) if hits else "ochiq PAN topilmadi (%d bayt tekshirildi)" % len(raw))
EOF
}
audit_try_update() { # audit yozuvini o'zgartirishga urinish
  "$PY" - "$DEMO/sb/mpay.db" <<'EOF'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
try:
    c.execute("UPDATE vault_audit SET details='{}' WHERE seq=2"); c.commit(); print("UPDATE o'tdi")
except sqlite3.DatabaseError as e:
    print("UPDATE rad etildi:", e)
EOF
}
audit_tamper() { # hujumchi: trigger'ni o'chirib, 2-yozuvni o'zgartiradi
  "$PY" - "$DEMO/sb/mpay.db" <<'EOF'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute("DROP TRIGGER vault_audit_no_update")
c.execute("""UPDATE vault_audit SET details='{"tampered":true}' WHERE seq=2"""); c.commit()
print("trigger o'chirildi, seq 2 o'zgartirildi")
EOF
}

cargo build -q -p mpay-server -p mpay-terminal-sim
SRV="$ROOT/target/debug/mpay-server$EXE"
TSIM="$ROOT/target/debug/mpay-tsim$EXE"
mkdir -p "$DEMO"
rm -rf "$DEMO/sb" "$DEMO"/*.json "$DEMO"/*.log

step "1. Bitta binar, HSM abstraksiyasi, post-kvant identifikator (1 daqiqa)"
say "mpay-server init: kalitlar KeyStore'da (sandbox: memory; bankda PKCS#11 HSM), TLS, API kalitlari."
pause
show "PQ Link server barmoq izi" "$SRV" init --dir "$DEMO/sb" --listen "127.0.0.1:$PORT" --tls
"$SRV" serve --config "$DEMO/sb/mpay.toml" 2> "$DEMO/server.log" &
SERVER_PID=$!
URL="https://localhost:$PORT"
for _ in $(seq 1 100); do
  curl -sf --cacert "$DEMO/sb/tls-cert.pem" "$URL/healthz" > /dev/null && break
  sleep 0.2
done
show '"status":"ok"' curl -s --cacert "$DEMO/sb/tls-cert.pem" "$URL/healthz"

mapfile -t PANS < <(grep -E '^pan = ' "$DEMO/sb/mpay.toml" | sed -E 's/pan = "([0-9]+)"/\1/')
GREEN="${PANS[0]}"; POOR="${PANS[1]}"; OFFLINE="${PANS[4]}"
T() { local phone="$1"; shift; "$TSIM" --server "$URL" --sandbox "$DEMO/sb" --wallet "$DEMO/$phone.json" "$@"; }
luhn_pan() {
  "$PY" -c "import sys
p=sys.argv[1]; s=0
for i,ch in enumerate(reversed(p)):
    d=int(ch)
    if i%2==0:
        d*=2
        d-=9 if d>9 else 0
    s+=d
print(p+str((10-s%10)%10))" "$1"
}

step "2. Tokenizatsiya: PQ Link + Android Key Attestation + Vault (1,5 daqiqa)"
say "Telefon A kartani qo'shadi: X25519+ML-KEM-768 kalit almashinuvi, Ed25519+ML-DSA-65 imzo,"
say "qurilma attestatsiyasi (StrongBox). Shield ID&V qaror beradi; Vault FPAN'ni shifrlab, DPAN chiqaradi."
pause
show "faol" T A provision --pan "$GREEN" --expiry 3112
show "yaroqli" T A status
say "Bazada ochiq PAN yo'q (envelope AES-256-GCM, qidiruv — HMAC indeks):"
show "ochiq PAN topilmadi" db_scan_pans

step "3. Tap-to-pay: EMV-ga o'xshash kriptogramma, ARPC, CDCVM (1,5 daqiqa)"
say "Kichik summa: karta ARQC hisoblaydi (LUK), emitent tekshiradi, ARPC kartada tasdiqlanadi."
pause
show "kod 00 (APPROVED).*ARPC: to'g'ri" T A tap --amount 12500.00
say "1 000 000 so'mdan katta: karta biometriyasiz rad etadi (6986 — 'telefonda tasdiqlang')."
pause
show "6986" T A tap --amount 2000000
show "kod 00" T A tap --amount 2000000 --cdcvm
show "yangi LUK" T A replenish

step "4. Shield: real-time fraud va ID&V (2 daqiqa)"
say "Karta testlash namunasi: veb-merchantda ketma-ket kichik summalar → skor oshadi → 59."
pause
found=""
for _ in $(seq 1 9); do
  out="$(T A tap --amount 500 --merchant WEB0000000003 2>&1 || true)"
  echo "$out" | sed 's/^/    /'
  if echo "$out" | grep -q "kod 59 (RISK_DECLINE)"; then found=1; break; fi
done
[ -n "$found" ] || { echo "XATO: 59 kutilgan edi"; exit 1; }
say "O'sha kartani boshqa telefonga qo'shish (ATO xavfi) → YELLOW, step-up OTP."
pause
show "OTP talab qilinadi" T C provision --pan "$GREEN" --expiry 3112
say "Bitta telefonga ko'p karta (qurilma fermasi) → RED."
pause
for i in 1 2 3 4 5; do
  T D provision --pan "$(luhn_pan "99001210000$(printf '%04d' $((5000 + i)))")" --expiry 3112 > /dev/null 2>&1 || true
done
show "RAD ETILDI: ID&V Red.*IDV_DEVICE_FARM" T D provision --pan "$(luhn_pan 990012100005006)" --expiry 3112

step "5. Emitent javoblari: 51 va 91 (1 daqiqa)"
pause
show "faol" T B provision --pan "$POOR" --expiry 3112
show "kod 51 (INSUFFICIENT_FUNDS)" T B tap --amount 20000
show "faol" T E provision --pan "$OFFLINE" --expiry 3112
show "kod 91 (ISSUER_OFFLINE)" T E tap --amount 100

step "6. Audit va loglar (1,5 daqiqa)"
say "Server loglarida faqat maskalangan PAN va token ID:"
pause
show '\*\*\*\*\*\*' sh -c "grep -oE '(pan|dpan)=99[0-9]{4}[*]{6}[0-9]{4}' '$DEMO/server.log' | sort | uniq -c"
for p in "${PANS[@]}"; do
  if grep -q "$p" "$DEMO/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
done
kill "$SERVER_PID"; wait "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
say "Audit log append-only (SQLite trigger) va xesh-zanjirli:"
show "audit zanjiri to'g'ri" env RUST_LOG=error "$SRV" audit-verify --config "$DEMO/sb/mpay.toml"
show "append-only" audit_try_update
say "Hujumchi trigger'ni o'chirib yozuvni o'zgartirsa ham — zanjir buzilganini ko'ramiz:"
pause
show "trigger o'chirildi" audit_tamper
show "audit zanjiri buzilgan: seq 2" env RUST_LOG=error "$SRV" audit-verify --config "$DEMO/sb/mpay.toml"

step "Yakun"
say "Telefon bilan qism (ixtiyoriy): docs/android-testing.md §3 — wallet-demo + terminal-app NFC tap."
echo "DEMO OK"
