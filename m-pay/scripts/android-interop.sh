#!/usr/bin/env bash
# Kotlin (android/mpay-core) ↔ Rust (mpay-server) interop testi: PQ Link handshake, provisioning,
# HCE applet + terminal yadrosi → emitent, CDCVM, replay, LUK, YELLOW/OTP, attestatsiya siyosati.
#   bash scripts/android-interop.sh
# Talablar: JDK 21 (Android Studio JBR yoki JAVA_HOME).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${MPAY_INTEROP_PORT:-18090}"
WORK="$(mktemp -d)"
SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
  if [ -n "${TLS_PID:-}" ]; then kill "$TLS_PID" 2>/dev/null || true; wait "$TLS_PID" 2>/dev/null || true; fi
  if [ -n "${SMSGW_PID:-}" ]; then kill "$SMSGW_PID" 2>/dev/null || true; wait "$SMSGW_PID" 2>/dev/null || true; fi
  rm -rf "$WORK"
}
trap cleanup EXIT

EXE=""
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) EXE=".exe" ;; esac
if [ -z "${JAVA_HOME:-}" ] && [ -d "/c/Program Files/Android/Android Studio/jbr" ]; then
  export JAVA_HOME="C:/Program Files/Android/Android Studio/jbr"
fi

cargo build -q -p mpay-server -p mpay-smsgw
SRV="target/debug/mpay-server$EXE"
"$SRV" init --dir "$WORK/sb" --listen "127.0.0.1:$PORT" > /dev/null

# 2-faza P2.1: virtual SMS shlyuzi — OTP karta egasining (fiktiv) telefoniga webhook orqali.
SMS_PORT=$((PORT + 2))
export MPAY_SMS_TOKEN="interop-$RANDOM$RANDOM"
"target/debug/mpay-smsgw$EXE" --listen "127.0.0.1:$SMS_PORT" 2> "$WORK/smsgw.log" &
SMSGW_PID=$!
sed -i 's/^channel = "sandbox"$/channel = "webhook"/' "$WORK/sb/mpay.toml"
sed -i "s|^# \[otp.webhook\]|[otp.webhook]|; s|^# url = \"http://127.0.0.1:47700/send\"|url = \"http://127.0.0.1:$SMS_PORT/send\"|; s|^# token_env = |token_env = |" "$WORK/sb/mpay.toml"
grep -q '^\[otp.webhook\]' "$WORK/sb/mpay.toml" || { echo "XATO: [otp.webhook] yoqilmadi"; exit 1; }
export MPAY_SMSGW="http://127.0.0.1:$SMS_PORT"
"$SRV" serve --config "$WORK/sb/mpay.toml" 2> "$WORK/server.log" &
SERVER_PID=$!
for _ in $(seq 1 100); do
  curl -sf "http://127.0.0.1:$PORT/healthz" > /dev/null && break
  sleep 0.2
done

# 1-faza P1.4: TLS + mTLS sandbox va terminal paketi.
TLS_PORT=$((PORT + 1))
"$SRV" init --dir "$WORK/tls" --listen "127.0.0.1:$TLS_PORT" --tls > /dev/null
# P1.6: keyingi PQ Link identifikatori e'lon qilinadi (Kotlin tasdiqni tekshiradi).
"$SRV" identity-next --config "$WORK/tls/mpay.toml" --version 2 > /dev/null
printf '
[pqlink.next]
mldsa_blob = "pqlink-mldsa65.v2.blob"
ed25519_label = "mpay.srv-ed25519.v2"
' >> "$WORK/tls/mpay.toml"
# ADR-0014: oflayn ildiz imzolagan bekor qilish ro'yxati (Kotlin tekshiradi).
ROOT_FP=$("$SRV" root-keygen --out "$WORK/root-key.json" | sed -n 's/^root_fingerprint: //p')
"$SRV" revoke --root-key "$WORK/root-key.json" --version 3 --fp "$(printf 'cd%.0s' $(seq 1 32))" \
  --out "$WORK/tls/revocations.json" > /dev/null
# [pqlink] jadvaliga (enrollment qatoridan keyin) qo'shiladi.
sed -i "/^enrollment_nonce_ttl_secs = /a root_fingerprint = \"$ROOT_FP\"" "$WORK/tls/mpay.toml"
sed -i "/^enrollment_nonce_ttl_secs = /a revocations = \"revocations.json\"" "$WORK/tls/mpay.toml"
export MPAY_ROOT_FP="$ROOT_FP"
"$SRV" terminal-bundle --config "$WORK/tls/mpay.toml" --url "https://127.0.0.1:$TLS_PORT" \
  --out "$WORK/terminal-bundle.json" > /dev/null
"$SRV" serve --config "$WORK/tls/mpay.toml" 2> "$WORK/server-tls.log" &
TLS_PID=$!
for _ in $(seq 1 100); do
  curl -sfk "https://127.0.0.1:$TLS_PORT/healthz" > /dev/null && break
  sleep 0.2
done
export MPAY_INTEROP_TLS_URL="https://127.0.0.1:$TLS_PORT"
export MPAY_TLS_SANDBOX_DIR="$WORK/tls"
export MPAY_TERMINAL_BUNDLE="$WORK/terminal-bundle.json"

export MPAY_INTEROP_URL="http://127.0.0.1:$PORT"
export MPAY_SANDBOX_DIR="$WORK/sb"
(cd android && ./gradlew :mpay-core:test --tests 'uz.mpay.core.InteropTest' --rerun-tasks --no-daemon --console=plain) \
  | grep -E "PASSED|FAILED|SKIPPED|server fp|PQ Link|token |avtorizatsiya|pin|keyingi|bekor|almashtirildi|SMS|Exception|BUILD"

echo "== Server logida ochiq PAN yo'q"
for p in $(grep -E '^pan = ' "$WORK/sb/mpay.toml" | sed -E 's/pan = "([0-9]+)"/\1/'); do
  if grep -q "$p" "$WORK/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
done
echo "== Server va shlyuz loglarida OTP va to'liq telefon yo'q"
if grep -qE '\+9980{7}[0-9]{2}' "$WORK/server.log" "$WORK/smsgw.log"; then echo "XATO: logda to'liq telefon"; exit 1; fi
if grep -qE 'kodi [0-9]{6}' "$WORK/server.log" "$WORK/smsgw.log"; then echo "XATO: logda OTP"; exit 1; fi
echo "INTEROP OK"
