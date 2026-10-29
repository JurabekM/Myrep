#!/usr/bin/env bash
# Falokatdan tiklash mashqi (ADR-0028, checklist JM-11): host butunlay yo'qoldi deb hisoblanadi.
#
#   bash scripts/dr-drill.sh
#
# 1. Toza compose muhiti (loyiha `mpay-dr`, portlar 28443/29090).
# 2. Telefon (mpay-tsim hamyoni host'dagi vaqtinchalik papkada — "telefon" falokatdan omon qoladi):
#    karta qo'shiladi, to'lov `00`.
# 3. Shifrlangan zaxira (`deploy/backup.sh`).
# 4. Falokat: `down -v` — konteynerlar va BARCHA hajmlar (DB, replika, WAL arxivi, HSM tokeni, holat).
# 5. `deploy/dr-restore.sh` — bo'sh muhitga tiklash, bosqichlar vaqti (RTO).
# 6. Xuddi shu telefon, xuddi shu token va LUK bilan to'lov `00` (ARQC → HSM'dagi IMK, PQ Link
#    identifikatori, token va emitent hisobi — hammasi tiklangan); solishtirish toza; loglarda PAN yo'q.
# Natija: docs/load/dr-drill.json. MPAY_KEEP=1 — oxirida muhit o'chirilmaydi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && (pwd -W 2>/dev/null || pwd))"
D="$ROOT/deploy"
export MSYS_NO_PATHCONV=1
export COMPOSE_PROJECT_NAME=mpay-dr
export MPAY_API_PORT=28443 MPAY_PROMETHEUS_PORT=29090
DC=(docker compose -f "$D/docker-compose.yml" -f "$D/docker-compose.test.yml")
PHONE="$(mktemp -d)"
BK="$(mktemp -d)"
chmod 777 "$PHONE"   # konteynerdagi mpay (uid 10001) hamyon faylini yoza olsin
# Bind mount uchun host yo'li: Git Bash'da `/tmp/...` Docker'ga VM ichidagi yo'l bo'lib o'tadi.
PHONE_HOST="$(cd "$PHONE" && (pwd -W 2>/dev/null || pwd))"
mkdir -p "$ROOT/docs/load"

cleanup() {
  if [ "${MPAY_KEEP:-}" != 1 ]; then
    "${DC[@]}" --profile test down -v --remove-orphans >/dev/null 2>&1 || true
    # "Telefon" fayllarini konteyner (uid 10001) yozgan — Linux'da host foydalanuvchisi o'chira olmaydi.
    docker run --rm --user 0 -v "$PHONE_HOST:/phone" --entrypoint sh mpay-server:local \
      -c 'rm -rf /phone/sb /phone/wallet.json' >/dev/null 2>&1 || true
    rm -rf "$PHONE" "$BK" || true
  fi
}
trap cleanup EXIT

# Telefon: dasturiy hamyon + terminal, sandbox katalogi (CA, mTLS, API kalitlari) — holat hajmidan.
# Sandbox katalogi bir marta "telefon" papkasiga nusxalanadi: mpay-tsim unga terminal STAN hisoblagichini
# yozadi (holat hajmi faqat o'qish uchun) va u falokatdan omon qolishi kerak (aks holda takroriy STAN — 94).
T() {
  "${DC[@]}" run --rm --no-deps -T -v "$PHONE_HOST:/phone" --entrypoint sh loadgen -c \
    '[ -d /phone/sb ] || cp -r /var/lib/mpay/state /phone/sb
     exec mpay-tsim --server https://lb:8443 --sandbox /phone/sb --wallet /phone/wallet.json "$@"' \
    sh "$@" 2>&1
}
expect() {   # expect <naqsh> <buyruq...>
  local pat="$1"; shift
  local out; out="$("$@")" || true
  echo "$out" | sed 's/^/    /'
  echo "$out" | grep -q -- "$pat" || { echo "XATO: '$pat' kutilgan edi"; exit 1; }
}
wait_api() {
  for _ in $(seq 1 180); do
    curl -sfk "https://127.0.0.1:$MPAY_API_PORT/healthz" >/dev/null && return 0
    sleep 1
  done
  echo "XATO: API javob bermadi" >&2; exit 1
}

echo "== sirlar va image'lar"
bash "$D/init-secrets.sh"
docker build -q --target runtime -t mpay-server:local "$ROOT" >/dev/null
docker build -q --target loadgen -t mpay-loadgen:local "$ROOT" >/dev/null
docker build -q -t mpay-pgproxy:local "$D/pgproxy" >/dev/null
docker build -q -t mpay-keepalived:local "$D/keepalived" >/dev/null
# age kalitlari image ichida yaratiladi — image'lar yig'ilgandan keyin (toza runner'da image yo'q).
bash "$D/backup-keygen.sh"

echo "== 1. toza muhit"
"${DC[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
"${DC[@]}" up -d --no-build >/dev/null 2>&1
wait_api

echo "== 2. telefon: karta va to'lov"
GREEN="$("${DC[@]}" run --rm --no-deps -T --entrypoint sh bootstrap -c \
  "grep -m1 -E '^pan = ' /var/lib/mpay/state/mpay.toml" 2>/dev/null | sed -E 's/pan = "([0-9]+)"/\1/' | tr -d '\r')"
[ -n "$GREEN" ] || { echo "XATO: sandbox kartasi topilmadi"; exit 1; }
expect "faol" T provision --pan "$GREEN" --expiry 3112
expect "kod 00 (APPROVED).*ARPC: to'g'ri" T tap --amount 12500.00

echo "== 3. shifrlangan zaxira"
bash "$D/backup.sh" "$BK" | tail -1
SRC="$(ls -d "$BK"/*/ | head -1)"
SRC="${SRC%/}"

echo "== 4. FALOKAT: barcha konteynerlar va hajmlar o'chiriladi"
"${DC[@]}" --profile test down -v --remove-orphans >/dev/null 2>&1
left="$(docker volume ls -q --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" | wc -l | tr -d ' ')"
[ "$left" = 0 ] || { echo "XATO: $left ta hajm qoldi"; exit 1; }
echo "   hajmlar: 0 (DB, replika, WAL arxivi, HSM tokeni, holat — yo'q)"

echo "== 5. tiklash (bo'sh muhitga)"
OUT="$(bash "$D/dr-restore.sh" "$SRC" 2>&1)" || { echo "$OUT"; exit 1; }
echo "$OUT" | grep -v "Container\|Volume\|Network" | sed 's/^/   /'
RTO="$(echo "$OUT" | sed -n 's/^dr_restore_seconds=//p')"
wait_api

echo "== 6. o'sha telefon, o'sha token — to'lov"
expect "kod 00 (APPROVED).*ARPC: to'g'ri" T tap --amount 7000.00
# PQ Link: hamyon pinlagan server barmoq izi (HSM'dagi identifikator) va qurilma reyestri tiklangan.
expect "yangi LUK" T replenish
expect "yaroqli" T status
REC="$("${DC[@]}" run --rm --no-deps -T --entrypoint mpay-entrypoint bootstrap \
  mpay-server recon --config /var/lib/mpay/state/mpay.toml 2>/dev/null || true)"
echo "$REC" | sed 's/^/    /'
echo "$REC" | grep -q "Tafovut yo'q" || { echo "XATO: solishtirishda tafovut"; exit 1; }

echo "== loglar: ochiq PAN va sirlar"
LOGS="$(mktemp)"
"${DC[@]}" logs --no-color > "$LOGS" 2>&1
if grep -q "$GREEN" "$LOGS"; then echo "XATO: logda ochiq PAN"; exit 1; fi
for s in pg_password pg_repl_password hsm_pin shield_key sms_token; do
  if grep -qF "$(cat "$D/secrets/$s")" "$LOGS"; then echo "XATO: logda sir ($s)"; exit 1; fi
done
rm -f "$LOGS"

created="$(sed -n 's/^created_utc=//p' "$SRC/MANIFEST")"
cat > "$ROOT/docs/load/dr-drill.json" <<JSON
{
  "scenario": "host yo'qoldi: barcha konteyner va hajmlar o'chirildi, shifrlangan zaxiradan tiklandi",
  "backup_created_utc": "$created",
  "restore_seconds": ${RTO:-null},
  "payment_after_restore": "00",
  "recon": "clean"
}
JSON
echo "   RTO (tiklash skripti): ${RTO:-?} s"
echo "DR DRILL OK"
