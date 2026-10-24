#!/usr/bin/env bash
# Fuzz kampaniyasi: barcha cargo-fuzz maqsadlari, har biri SECONDS soniya (standart 300).
#   bash scripts/fuzz-campaign.sh [SECONDS] [maqsad ...]
# Talablar: nightly toolchain, cargo-fuzz. Windows MSVC'da ASan DLL papkasi PATH'da bo'lishi kerak
# (`clang_rt.asan_dynamic-x86_64.dll`, VS Build Tools `bin/Hostx64/x64`).
# Natija: docs/fuzz-report.md uchun jadval qatorlari (stdout) va fuzz/artifacts/<maqsad>/ (crash bo'lsa).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/fuzz"
SECS="${1:-300}"
shift || true
TARGETS=("$@")
if [ ${#TARGETS[@]} -eq 0 ]; then
  mapfile -t TARGETS < <(cargo +nightly fuzz list)
fi
JOBS="${FUZZ_PARALLEL:-3}"

cargo +nightly fuzz build -O >/dev/null
mkdir -p logs

run() {
  local t="$1"
  mkdir -p "corpus/$t"
  # Repodagi boshlang'ich kirishlar (seeds/<maqsad>) — chuqur holatlarga tez yetish uchun.
  local seeds=()
  [ -d "seeds/$t" ] && seeds=("seeds/$t")
  # -rss_limit_mb: PQ maqsadlari (ML-KEM/ML-DSA) uchun yetarli, xotira oqishini ushlaydi.
  cargo +nightly fuzz run -O "$t" "corpus/$t" "${seeds[@]}" -- \
    -max_total_time="$SECS" -dict=emv.dict -rss_limit_mb=2048 -print_final_stats=1 \
    > "logs/$t.log" 2>&1 && echo "OK $t" || echo "CRASH $t"
}

pids=()
for t in "${TARGETS[@]}"; do
  run "$t" &
  pids+=($!)
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 1; done
done
status=0
for p in "${pids[@]}"; do wait "$p" || status=1; done

echo
echo "| Maqsad | Vaqt, s | Yugurishlar | exec/s | Qamrov (cov) | Korpus | Natija |"
echo "|---|---|---|---|---|---|---|"
for t in "${TARGETS[@]}"; do
  log="logs/$t.log"
  runs=$(grep -o 'stat::number_of_executed_units: *[0-9]*' "$log" | grep -o '[0-9]*$' || echo "?")
  eps=$(grep -o 'stat::average_exec_per_sec: *[0-9]*' "$log" | grep -o '[0-9]*$' || echo "?")
  cov=$(grep -oE '#[0-9]+[[:space:]]+(DONE|pulse|NEW|REDUCE)[[:space:]]+cov: [0-9]+' "$log" | tail -1 | grep -oE '[0-9]+$' || echo "?")
  corp=$(find "corpus/$t" -type f | wc -l)
  if grep -qE 'ERROR: libFuzzer|panicked|deadly signal|AddressSanitizer' "$log"; then res="**CRASH**"; status=1; else res="toza"; fi
  echo "| \`$t\` | $SECS | $runs | $eps | $cov | $corp | $res |"
done
exit $status
