#!/usr/bin/env bash
# 2-faza P2.5 (ADR-0020): compose muhitining to'liq sinovi — Docker Desktop yoki Linux Docker.
#
#   bash scripts/compose-test.sh [SECONDS] [CONCURRENCY]
#
# 1. Image'lar (runtime + loadgen), alohida compose loyihasi `mpay-test` (portlar 18443/19090).
# 2. TLS end-to-end: nginx orqali kelgan sertifikat = API sertifikati (L4, TLS ochilmaydi).
# 3. Yuk nginx orqali (TLS + mTLS, PROXY protocol); o'rtada api-1 to'xtatiladi (SIGTERM, graceful),
#    Prometheus'da MpayInstanceDown ogohlantirishi kutiladi, so'ng api-1 qayta ishga tushadi.
# 4. Zaxira → alohida bazaga tiklash → audit xesh-zanjiri tekshiruvi.
# 5. Loglarda ochiq PAN va sirlar yo'qligi.
# Natija: docs/load/p2.5-compose.json. MPAY_KEEP=1 — oxirida muhit o'chirilmaydi.
set -euo pipefail

# Git Bash (Windows): `pwd -W` — docker.exe `/c/...` yo'lini tushunmaydi.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && (pwd -W 2>/dev/null || pwd))"
D="$ROOT/deploy"
SECS="${1:-90}"
CONC="${2:-32}"
export MSYS_NO_PATHCONV=1
export COMPOSE_PROJECT_NAME=mpay-test
export MPAY_API_PORT=18443 MPAY_PROMETHEUS_PORT=19090
DC=(docker compose -f "$D/docker-compose.yml" -f "$D/docker-compose.test.yml")
PROM="http://127.0.0.1:$MPAY_PROMETHEUS_PORT"
PY="$(command -v python3 || command -v python)"
LOADLOG="$(mktemp)"
mkdir -p "$ROOT/docs/load"

cleanup() {
  if [ "${MPAY_KEEP:-}" != 1 ]; then
    "${DC[@]}" --profile test down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

prom_q() {   # $1 PromQL → birinchi qiymat (yo'q bo'lsa bo'sh)
  curl -sG "$PROM/api/v1/query" --data-urlencode "query=$1" | "$PY" -c \
    'import json,sys; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else "")'
}
alerts() {   # faol ogohlantirishlar: nomi=holati
  curl -s "$PROM/api/v1/alerts" | "$PY" -c \
    'import json,sys; print(" ".join(sorted(a["labels"]["alertname"]+"="+a["state"] for a in json.load(sys.stdin)["data"]["alerts"])))'
}

echo "== sirlar va image'lar"
bash "$D/init-secrets.sh"
docker build -q --target runtime -t mpay-server:local "$ROOT" >/dev/null
docker build -q --target loadgen -t mpay-loadgen:local "$ROOT" >/dev/null
docker run --rm --entrypoint promtool -v "$D/prometheus:/etc/prometheus:ro" prom/prometheus:v3.5.0 \
  check config /etc/prometheus/prometheus.yml

echo "== muhit ishga tushmoqda"
"${DC[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
"${DC[@]}" up -d --no-build
for _ in $(seq 1 120); do
  curl -sfk "https://127.0.0.1:$MPAY_API_PORT/healthz" >/dev/null && break
  sleep 1
done
curl -sfk "https://127.0.0.1:$MPAY_API_PORT/healthz"; echo
"${DC[@]}" ps --format "table {{.Service}}\t{{.Status}}"

echo "== TLS end-to-end (nginx sertifikatni almashtirmaydi)"
"${DC[@]}" run --rm --no-deps -T --entrypoint sh loadgen -c '
  a=$(echo | openssl s_client -connect lb:8443 -servername lb 2>/dev/null | openssl x509 -noout -fingerprint -sha256)
  b=$(openssl x509 -in /var/lib/mpay/state/tls-cert.pem -noout -fingerprint -sha256)
  echo "lb:  $a"; echo "api: $b"; [ "$a" = "$b" ]'

echo "== yuk: $SECS s, $CONC ishchi, nginx orqali; api-1 o'rtada to'xtatiladi"
# Natija JSON — stdout'da (host papkasini konteynerga ulamasdan: Linux'da uid 10001 unga yoza olmaydi),
# jarayon logi — stderr'da.
"${DC[@]}" run --rm --no-deps -T --entrypoint sh loadgen -c \
  "mpay-load run --dir /var/lib/mpay/state --server https://lb:8443 --cards ${MPAY_LOAD_CARDS:-200} \
   --concurrency $CONC --duration $SECS --out /tmp/r.json >&2 && cat /tmp/r.json" \
  > "$ROOT/docs/load/p2.5-compose.json" 2> "$LOADLOG" &
LOAD=$!
# Provisioning (~5 s) + avtorizatsiya boshlanishi.
sleep 25
echo "-- api-1 to'xtatilmoqda (SIGTERM)"
t0=$(date +%s)
"${DC[@]}" stop api-1
echo "   to'xtadi: $(( $(date +%s) - t0 )) s"
FIRED=""
for _ in $(seq 1 12); do
  sleep 5
  a="$(alerts)"
  if echo "$a" | grep -q "MpayInstanceDown=firing"; then FIRED=1; break; fi
done
echo "   ogohlantirishlar: $a"
echo "-- api-1 qayta ishga tushirilmoqda"
"${DC[@]}" start api-1
wait $LOAD || { cat "$LOADLOG"; exit 1; }
grep -v "^ Container" "$LOADLOG"
rm -f "$LOADLOG"
[ -n "$FIRED" ] || { echo "XATO: MpayInstanceDown ishlamadi"; exit 1; }

echo "== Prometheus"
sleep 12
for q in 'sum(mpay_authorizations_total)' 'sum by (instance) (mpay_authorizations_total)' \
         'sum(mpay_shield_degraded_total)' 'sum(mpay_proxy_protocol_rejected_total)' \
         'min(mpay_db_up)' 'max(mpay_shield_cards)' \
         'histogram_quantile(0.99, sum by (le) (rate(mpay_http_request_duration_seconds_bucket{route="/v1/authorizations"}[2m])))'; do
  echo "   $q = $(prom_q "$q")"
done
# Qayta ishga tushgan api-1 hisoblagichi noldan boshlanadi (va keep-alive ulanishlar api-2 da qoladi) —
# to'xtatishdan oldingi qiymat Prometheus tarixidan.
for i in api-1 api-2; do
  n="$(prom_q "max(max_over_time(mpay_authorizations_total{instance=\"$i:9464\"}[10m]))")"
  echo "   $i: $n ta avtorizatsiya (eng katta qiymat)"
  [ -n "$n" ] && [ "${n%.*}" -gt 0 ] || { echo "XATO: $i avtorizatsiya olmagan"; exit 1; }
done
[ "$(prom_q 'sum(mpay_proxy_protocol_rejected_total)')" = 0 ] || { echo "XATO: PROXY sarlavhasi rad etilgan"; exit 1; }

echo "== zaxira va tiklash"
BK="$(mktemp -d)"
bash "$D/backup.sh" "$BK"
bash "$D/restore.sh" "$BK"/* --verify
rm -rf "$BK"

echo "== loglar: ochiq PAN va sirlar"
LOGS="$(mktemp)"
"${DC[@]}" logs --no-color > "$LOGS" 2>&1
if grep -qE "99001277[0-9]{8}" "$LOGS"; then echo "XATO: logda ochiq PAN"; exit 1; fi
for s in pg_password hsm_pin shield_key sms_token; do
  if grep -qF "$(cat "$D/secrets/$s")" "$LOGS"; then echo "XATO: logda sir ($s)"; exit 1; fi
done
echo "   $(wc -l < "$LOGS") qator log — PAN va sir yo'q"
grep -c "PROXY protocol sarlavhasi yaroqsiz" "$LOGS" || true
rm -f "$LOGS"
echo "COMPOSE TEST OK"
