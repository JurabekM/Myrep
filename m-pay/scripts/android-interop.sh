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
  rm -rf "$WORK"
}
trap cleanup EXIT

EXE=""
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) EXE=".exe" ;; esac
if [ -z "${JAVA_HOME:-}" ] && [ -d "/c/Program Files/Android/Android Studio/jbr" ]; then
  export JAVA_HOME="C:/Program Files/Android/Android Studio/jbr"
fi

cargo build -q -p mpay-server
SRV="target/debug/mpay-server$EXE"
"$SRV" init --dir "$WORK/sb" --listen "127.0.0.1:$PORT" > /dev/null
"$SRV" serve --config "$WORK/sb/mpay.toml" 2> "$WORK/server.log" &
SERVER_PID=$!
for _ in $(seq 1 100); do
  curl -sf "http://127.0.0.1:$PORT/healthz" > /dev/null && break
  sleep 0.2
done

export MPAY_INTEROP_URL="http://127.0.0.1:$PORT"
export MPAY_SANDBOX_DIR="$WORK/sb"
(cd android && ./gradlew :mpay-core:test --tests 'uz.mpay.core.InteropTest' --rerun-tasks --no-daemon --console=plain) \
  | grep -E "PASSED|FAILED|SKIPPED|server fp|PQ Link|token |avtorizatsiya|Exception|BUILD"

echo "== Server logida ochiq PAN yo'q"
for p in $(grep -E '^pan = ' "$WORK/sb/mpay.toml" | sed -E 's/pan = "([0-9]+)"/\1/'); do
  if grep -q "$p" "$WORK/server.log"; then echo "XATO: logda ochiq PAN"; exit 1; fi
done
echo "INTEROP OK"
