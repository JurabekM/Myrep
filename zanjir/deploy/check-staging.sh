#!/usr/bin/env bash
# Staging qabul sinovi (11-faza mezoni, ADR-0015):
#   1) `zanjir up staging` — bitta buyruq; 2) HTTPS smoke (Caddy CA bilan): health, xavfsizlik sarlavhalari, /metrics
#   yopiq, http → https; 3) Dart E2E (ikki qurilma, sync, reja, protokol) staging'ga TLS orqali; 4) shifrlangan zaxira;
#   5) zaxirani YANGI bo'sh PostgreSQL'ga tiklash va har bir jadval nazorat yig'indisini jonli baza bilan solishtirish.
# Ishlatish: deploy/check-staging.sh   (staging ko'tarilgan holda qoladi; tiklash bazasi o'chiriladi)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
ENVF="$DIR/environments/staging.env"
TMP="$(mktemp -d)"
DRILL=zanjir-staging-restorecheck
dc() { docker compose --project-directory "$DIR" -f "$DIR/compose.yaml" --env-file "$ENVF" "$@"; }
cleanup() { dc -p "$DRILL" down -v >/dev/null 2>&1 || true; rm -rf "$TMP"; }
trap cleanup EXIT
step() { echo; echo "== $*"; }

step "1. staging: bitta buyruq"
"$DIR/zanjir" up staging
var() { grep -E "^$1=" "$ENVF" | tail -1 | cut -d= -f2-; }
DOMAIN="$(var ZANJIR_DOMAIN)"; HTTPS="$(var ZANJIR_HTTPS_PORT)"; HTTP="$(var ZANJIR_HTTP_PORT)"
BASE="https://$DOMAIN:$HTTPS"

step "2. HTTPS smoke ($BASE)"
dc -p zanjir-staging exec -T caddy cat /data/caddy/pki/authorities/local/root.crt > "$TMP/ca.crt"
C=(curl -sS --noproxy '*' --resolve "$DOMAIN:$HTTPS:127.0.0.1" --cacert "$TMP/ca.crt")
[[ "$("${C[@]}" "$BASE/readyz")" == '{"status":"ready"}' ]] || { echo "readyz emas"; exit 1; }
headers="$("${C[@]}" -D - -o /dev/null "$BASE/healthz")"
for h in "strict-transport-security: max-age=31536000" "x-content-type-options: nosniff" "x-frame-options: DENY" \
  "cache-control: no-store"; do
  grep -qi "^$h" <<<"$headers" || { echo "sarlavha yo'q: $h"; exit 1; }
done
grep -qi "^server:" <<<"$headers" && { echo "Server sarlavhasi ochiq"; exit 1; }
[[ "$("${C[@]}" -o /dev/null -w '%{http_code}' "$BASE/metrics")" == 404 ]] || { echo "/metrics ochiq"; exit 1; }
code="$(curl -sS --noproxy '*' --resolve "$DOMAIN:$HTTP:127.0.0.1" -o /dev/null -w '%{http_code}' "http://$DOMAIN:$HTTP/")"
[[ "$code" == 308 ]] || { echo "http → https yo'naltirilmadi ($code)"; exit 1; }
echo "smoke: OK"

step "3. E2E (Dart) staging'ga TLS orqali"
(cd "$ROOT/packages/zanjir_data" && ZANJIR_E2E_URL="$BASE" ZANJIR_E2E_CA="$TMP/ca.crt" dart test -P e2e-run test/e2e \
  --reporter=compact 2>&1 | tail -1) | tee "$TMP/e2e.log"
grep -q "All tests passed" "$TMP/e2e.log" || { echo "E2E yiqildi"; exit 1; }

step "4. shifrlangan zaxira"
out="$("$DIR/zanjir" backup staging)"; echo "$out"
file="$(grep -o 'zanjir-[0-9TZ]*\.dump\.age' <<<"$out" | head -1)"
bdir="$(var ZANJIR_BACKUP_DIR)"; [[ "$bdir" = /* ]] || bdir="$DIR/${bdir#./}"
[[ "$(head -c 21 "$bdir/$file")" == "age-encryption.org/v1" ]] || { echo "zaxira shifrlanmagan"; exit 1; }
if grep -aq "MEASUREMENT_ADDED" "$bdir/$file"; then echo "zaxirada ochiq matn"; exit 1; fi

# Har bir jadval: qatorlar soni va mazmun md5 (superuser, lokal socket); sxema — pg_dump --schema-only.
fingerprint() {
  dc -p "$1" exec -T -u postgres db psql -d zanjir -tA -v ON_ERROR_STOP=1 <<'SQL'
SELECT format('SELECT %L, count(*), md5(coalesce(string_agg(x::text, %L ORDER BY x::text), %L)) FROM public.%I x',
              tablename, '|', '', tablename)
FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename \gexec
SQL
  # `\restrict` — pg_dump har safar tasodifiy kalit yozadi (16.10+), sxema solishtirishga kirmaydi.
  echo "schema|$(dc -p "$1" exec -T -u postgres db pg_dump --schema-only --no-comments zanjir \
    | grep -vE '^(--|\\(un)?restrict )' | md5sum | cut -d' ' -f1)"
}
fingerprint zanjir-staging > "$TMP/live.txt"
grep -E '^(measurement|protocol|audit_event)\|' "$TMP/live.txt"
for t in measurement protocol audit_event; do
  n="$(grep "^$t|" "$TMP/live.txt" | cut -d'|' -f2)"; [[ "$n" -gt 0 ]] || { echo "$t bo'sh — sinov ma'nosiz"; exit 1; }
done

step "5a. tiklash mashqi: yangi bo'sh PostgreSQL ($DRILL)"
dc -p "$DRILL" up -d --wait db
dc -p "$DRILL" run --rm --no-deps -T -v "$DIR/environments/staging.age-key:/run/age-key:ro" backup \
  restore.sh "/backups/$file" /run/age-key
fingerprint "$DRILL" > "$TMP/drill.txt"
diff -u "$TMP/live.txt" "$TMP/drill.txt" || { echo "tiklangan baza farq qiladi"; exit 1; }
echo "tiklangan baza = jonli baza ($(wc -l < "$TMP/live.txt") qator nazorat)"
# Bo'sh bo'lmagan bazaga tiklash rad etiladi.
if dc -p "$DRILL" run --rm --no-deps -T -v "$DIR/environments/staging.age-key:/run/age-key:ro" backup \
  restore.sh "/backups/$file" /run/age-key >/dev/null 2>&1; then echo "bo'sh bo'lmagan bazaga tiklandi!"; exit 1; fi

step "5b. operator buyrug'i: zanjir restore staging (RUNBOOK)"
"$DIR/zanjir" restore staging "$bdir/$file" "$DIR/environments/staging.age-key" --confirm staging
fingerprint zanjir-staging > "$TMP/restored.txt"
diff -u "$TMP/live.txt" "$TMP/restored.txt" || { echo "tiklangan staging farq qiladi"; exit 1; }
echo "staging zaxiradan tiklandi, ma'lumot bir xil"
[[ "$("${C[@]}" "$BASE/readyz")" == '{"status":"ready"}' ]] || { echo "tiklashdan keyin readyz emas"; exit 1; }

echo; echo "STAGING QABUL SINOVI: OK"
