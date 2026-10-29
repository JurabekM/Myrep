#!/usr/bin/env bash
# Kotlin yadrosi (android/mpay-core) uchun Jazzer fuzzing: har @FuzzTest o'z `maxDuration` i bilan.
#   bash scripts/android-fuzz.sh [test ...]      # standart: hammasi
# Talablar: JDK 21 (Android Studio JBR). Topilma — `android/mpay-core/crash-*` (git'ga tushmaydi);
# tuzatilgach kirishni `src/test/resources/uz/mpay/core/FuzzTestsInputs/<test>/` ga qo'shing (regressiya).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/android"
if [ -z "${JAVA_HOME:-}" ] && [ -d "/c/Program Files/Android/Android Studio/jbr" ]; then
  export JAVA_HOME="C:/Program Files/Android/Android Studio/jbr"
fi
TESTS=("$@")
if [ ${#TESTS[@]} -eq 0 ]; then
  mapfile -t TESTS < <(grep -A1 "@FuzzTest" mpay-core/src/test/kotlin/uz/mpay/core/FuzzTests.kt \
    | sed -n 's/^ *fun \([a-zA-Z0-9]*\)(.*/\1/p')
fi
mkdir -p mpay-core/build/fuzz-logs
status=0
echo "| Test | Natija | Yugurishlar | exec/s |"
echo "|---|---|---|---|"
for t in "${TESTS[@]}"; do
  log="mpay-core/build/fuzz-logs/$t.log"
  if JAZZER_FUZZ=1 ./gradlew -q :mpay-core:test --tests "uz.mpay.core.FuzzTests.$t" > "$log" 2>&1; then
    res="toza"
  else
    res="**TOPILMA**"; status=1
  fi
  runs=$(grep -oE 'Done [0-9]+ runs' "$log" | grep -oE '[0-9]+' | tail -1 || true)
  eps=$(grep -oE 'exec/s: [0-9]+' "$log" | tail -1 | grep -oE '[0-9]+' || true)
  echo "| \`$t\` | $res | ${runs:-?} | ${eps:-?} |"
done
exit $status
