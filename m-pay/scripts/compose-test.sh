#!/usr/bin/env bash
# 2-faza P2.5 (ADR-0020): compose muhitining to'liq sinovi — Docker Desktop yoki Linux Docker.
#
#   bash scripts/compose-test.sh [SECONDS] [CONCURRENCY]
#
# 1. Image'lar (runtime + loadgen), alohida compose loyihasi `mpay-test` (portlar 18443/19090).
# 2. TLS end-to-end: nginx orqali kelgan sertifikat = API sertifikati (L4, TLS ochilmaydi).
# 3. Yuk nginx orqali (TLS + mTLS, PROXY protocol); o'rtada api-1 to'xtatiladi (SIGTERM, graceful),
#    Prometheus'da MpayInstanceDown ogohlantirishi kutiladi, so'ng api-1 qayta ishga tushadi.
#    Ogohlantirish Alertmanager orqali navbatchi kanaliga (virtual — smsgw `/alerts`) yetib boradi.
# 3a. Shield almashinuvi (ADR-0026): yetakchi Shield SIGKILL bilan o'ldiriladi — zaxira snapshot'dan
#     tiklab oladi, keyingi yukda API'lar mahalliy zaxiraga tushmaydi.
# 3b. PostgreSQL almashinuvi (ADR-0027): replika yetib olgach yetakchi SIGKILL bilan o'ldiriladi,
#     `pg-failover.sh` replikani ko'taradi (audit yozuvlari yo'qolmaydi), `pg-rejoin.sh` eski
#     yetakchini yangi yetakchining replikasi qiladi; keyingi yuk yangi yetakchiga yoziladi.
# 3c. nginx zaxirasi (ADR-0027): VIP egasi SIGKILL — VIP ikkinchi nginx'ga o'tadi, API VIP orqali
#     javob beradi; qaytgan nginx VIP'ni tortib olmaydi.
# 4. Shifrlangan zaxira (age): yukdan oldin asosiy nusxa (B1), keyin T lahza, yana faollik, ikkinchi
#    zaxira (B2) → alohida bazaga tiklash + audit; PITR: B1 + B2 WAL → T lahza — audit yozuvlari soni
#    T dagidek (keyingi faollik yo'q), audit xesh-zanjiri to'g'ri. B1 almashinuvdan oldin, T — keyin:
#    PITR yangi timeline bo'ylab tiklaydi.
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
    # Faqat shu yugurish yaratgan vaqtinchalik zaxira papkalari (shifrlangan, ~200 MB).
    rm -rf "${BK1:-}" "${BK2:-}"
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
docker build -q -t mpay-pgproxy:local "$D/pgproxy" >/dev/null
docker build -q -t mpay-keepalived:local "$D/keepalived" >/dev/null
docker run --rm --entrypoint promtool -v "$D/prometheus:/etc/prometheus:ro" prom/prometheus:v3.5.0 \
  check config /etc/prometheus/prometheus.yml
docker run --rm --entrypoint amtool -v "$D/alertmanager:/etc/alertmanager:ro" prom/alertmanager:v0.34.1 \
  check-config /etc/alertmanager/alertmanager.yml
bash "$D/backup-keygen.sh"
# shellcheck source=../deploy/lib-pg.sh
. "$(dirname "${BASH_SOURCE[0]}")/../deploy/lib-pg.sh"
sql() {   # $1 SQL → qiymat (joriy PostgreSQL yetakchisi — almashinuvdan keyin boshqa tugun)
  "${DC[@]}" exec -T "$(pg_primary)" psql -U mpay -d mpay -qAtc "$1" | tr -d '\r'
}
navbatchi() {   # virtual navbatchi kanalidagi ogohlantirishlar: nomi=holati
  "${DC[@]}" exec -T smsgw sh -c \
    'curl -s -H "Authorization: Bearer $(cat /run/secrets/sms_token)" http://localhost:47700/alerts' \
    | "$PY" -c 'import json,sys; print(" ".join(sorted({a["alertname"]+"="+a["status"] for a in json.load(sys.stdin)})))'
}
BK1="$(mktemp -d)"
BK2="$(mktemp -d)"

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

echo "== asosiy zaxira (B1, PITR boshlang'ich nuqtasi)"
bash "$D/backup.sh" "$BK1" | tail -1

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
# api-1 navbatchiga xabar yetguncha o'chiq qoladi: Alertmanager birinchi xabarni `group_wait` dan keyin
# yuboradi, undan oldin yopilgan ogohlantirish umuman yuborilmaydi (tez mashinada poyga).
NB=""
if [ -n "$FIRED" ]; then
  for _ in $(seq 1 24); do
    nb="$(navbatchi)"
    if echo "$nb" | grep -q "MpayInstanceDown=firing"; then NB=1; break; fi
    sleep 5
  done
  echo "   navbatchi kanali (Alertmanager → smsgw): $nb"
fi
echo "-- api-1 qayta ishga tushirilmoqda"
"${DC[@]}" start api-1
wait $LOAD || { cat "$LOADLOG"; exit 1; }
grep -v "^ Container" "$LOADLOG"
rm -f "$LOADLOG"
[ -n "$FIRED" ] || { echo "XATO: MpayInstanceDown ishlamadi"; exit 1; }
if [ -z "$NB" ]; then
  echo "XATO: ogohlantirish navbatchiga yetmadi"
  "${DC[@]}" logs --no-color --tail 40 alertmanager prometheus smsgw 2>&1 | grep -iE "error|warn|alert|notif" | tail -30
  exit 1
fi

echo "== Shield almashinuvi: yetakchi o'ldiriladi (SIGKILL)"
shield_health() {   # $1 xizmat → healthz JSON (ichki port)
  "${DC[@]}" exec -T "$1" curl -sfk https://localhost:8600/healthz 2>/dev/null || echo '{}'
}
jget() { "$PY" -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
LEADER=""
for s in shield shield-2; do
  [ "$(shield_health "$s" | jget '.get("leader")')" = True ] && LEADER="$s"
done
[ -n "$LEADER" ] || { echo "XATO: Shield yetakchisi yo'q"; exit 1; }
STANDBY=$([ "$LEADER" = shield ] && echo shield-2 || echo shield)
CARDS="$(shield_health "$LEADER" | jget '["cards"]')"
echo "   yetakchi: $LEADER ($CARDS karta), zaxira: $STANDBY"
# Oxirgi hodisalar snapshot'ga tushsin (snapshot_interval_secs = 10).
sleep 12
t0=$(date +%s)
"${DC[@]}" kill -s SIGKILL "$LEADER" >/dev/null
TOOK=""
for _ in $(seq 1 30); do
  sleep 1
  if [ "$(shield_health "$STANDBY" | jget '.get("leader")')" = True ]; then TOOK=1; break; fi
done
[ -n "$TOOK" ] || { echo "XATO: zaxira Shield yetakchilikni olmadi"; exit 1; }
H2="$(shield_health "$STANDBY")"
echo "   $STANDBY yetakchi: $(( $(date +%s) - t0 )) s ichida; $(echo "$H2" | jget '["cards"]') karta, epoch $(echo "$H2" | jget '["ha"]["epoch"]')"
[ "$(echo "$H2" | jget '["cards"]')" = "$CARDS" ] || { echo "XATO: snapshot'dan tiklangan kartalar soni $CARDS emas"; exit 1; }
# O'tishdan keyingi trafik — "T lahza" bosqichining yuki (alohida yuk bu yerda kartalarni yana bir
# qurilmaga qo'shib, keyingi bosqichda karta–qurilma qoidasiga tushirardi). Tekshiruv — o'sha yukdan keyin.
sleep 12
DEG1="$(prom_q 'sum(mpay_shield_degraded_total)')"
echo "   SHIELD_DEGRADED o'tishdan keyin: ${DEG1:-0}"
"${DC[@]}" start "$LEADER" >/dev/null
sleep 5
[ "$(shield_health "$LEADER" | jget '.get("leader")')" = False ] || { echo "XATO: qaytgan instansiya zaxira emas"; exit 1; }
echo "   $LEADER qaytdi — zaxira"

echo "== Prometheus"
sleep 12
for q in 'sum(mpay_authorizations_total)' 'sum by (instance) (mpay_authorizations_total)' \
         'sum(mpay_shield_degraded_total)' 'sum(mpay_proxy_protocol_rejected_total)' \
         'min(mpay_db_up)' 'max(mpay_shield_cards)' 'sum(mpay_shield_leader)' 'max(mpay_db_replicas)' \
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
# P2.6: har provisioning'da Play Integrity (mock) tokeni tekshirilgan.
pi="$(prom_q 'sum(max_over_time(mpay_integrity_checks_total{result="ok"}[10m]))')"
echo "   yaxlitlik tekshiruvlari (ok): $pi"
[ -n "$pi" ] && [ "${pi%.*}" -ge "${MPAY_LOAD_CARDS:-200}" ] || { echo "XATO: yaxlitlik tokeni tekshirilmagan"; exit 1; }

echo "== PostgreSQL almashinuvi: yetakchi o'ldiriladi (SIGKILL)"
r="$(prom_q 'max(mpay_db_replicas)')"
echo "   streaming replikalar (Prometheus): ${r:-0}"
[ "${r%.*}" = 1 ] || { echo "XATO: replika yetakchiga ulanmagan"; exit 1; }
PRIM="$(pg_primary)"
lag=""
for _ in $(seq 1 30); do
  lag="$(sql "SELECT COALESCE(MAX(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)), 0)::bigint FROM pg_stat_replication")"
  [ "$lag" = 0 ] && break
  sleep 1
done
A0="$(sql "SELECT count(*) FROM vault_audit")"
echo "   yetakchi: $PRIM, replika kechikishi: $lag bayt, audit=$A0"
t0=$(date +%s)
"${DC[@]}" kill -s SIGKILL "$PRIM" >/dev/null
bash "$D/pg-failover.sh" | sed 's/^/   /'
NEWP="$(pg_primary)"
A1="$(sql "SELECT count(*) FROM vault_audit")"
echo "   yangi yetakchi: $NEWP ($(( $(date +%s) - t0 )) s), audit=$A1"
[ "$NEWP" != "$PRIM" ] || { echo "XATO: yetakchi almashmadi"; exit 1; }
[ "$A1" = "$A0" ] || { echo "XATO: almashinuvda audit yozuvlari yo'qoldi ($A0 → $A1)"; exit 1; }
# Eski yetakchi qayta ishga tushirilsa — to'siq (ikkinchi yetakchi bo'lmaydi).
"${DC[@]}" start "$PRIM" >/dev/null 2>&1 || true
sleep 8
[ "$(pg_role "$PRIM")" != f ] || { echo "XATO: eski yetakchi to'siqsiz ishga tushdi (ikki yetakchi)"; exit 1; }
"${DC[@]}" logs --no-color --tail 5 "$PRIM" 2>&1 | grep -q "TO'SIQ" \
  || { echo "XATO: eski yetakchi logida to'siq xabari yo'q"; exit 1; }
echo "   eski yetakchi qayta ishga tushirilganda to'sildi"
bash "$D/pg-rejoin.sh" "$PRIM" | sed 's/^/   /'
[ "$(pg_role "$PRIM")" = t ] || { echo "XATO: $PRIM replika emas"; exit 1; }

echo "== nginx zaxirasi: VIP egasi o'ldiriladi (SIGKILL)"
# VIP orqali haqiqiy so'rov (TLS + PROXY protocol): lb-2 ham ishonchli proksi bo'lishi tekshiriladi.
vip_health() {
  "${DC[@]}" run --rm --no-deps -T --entrypoint sh loadgen -c \
    'curl -sfk --max-time 3 --resolve lb:8443:10.88.0.100 https://lb:8443/healthz >/dev/null && echo ok' \
    2>/dev/null || true
}
vip_holder() {
  for s in lb lb-2; do
    if "${DC[@]}" exec -T "$s" ip -4 addr show dev eth0 2>/dev/null | grep -q "10.88.0.100/"; then
      echo "$s"
    fi
  done
  return 0   # `set -e`: "VIP yo'q" — bo'sh natija, xato emas
}
H="$(vip_holder)"
[ -n "$H" ] || { echo "XATO: VIP hech bir nginx'da yo'q"; exit 1; }
[ "$(vip_health)" = ok ] || { echo "XATO: VIP orqali API javob bermadi"; exit 1; }
OTHER=$([ "$H" = lb ] && echo lb-2 || echo lb)
t0=$(date +%s)
"${DC[@]}" kill -s SIGKILL "$H" >/dev/null
MOVED=""
for _ in $(seq 1 20); do
  if [ "$(vip_holder)" = "$OTHER" ] && [ "$(vip_health)" = ok ]; then MOVED=1; break; fi
  sleep 1
done
[ -n "$MOVED" ] || { echo "XATO: VIP $OTHER ga o'tmadi"; exit 1; }
echo "   VIP: $H → $OTHER, $(( $(date +%s) - t0 )) s; API VIP orqali javob beradi"
"${DC[@]}" up -d --no-deps "$H" >/dev/null 2>&1
"${DC[@]}" restart "$H-vrrp" >/dev/null 2>&1
sleep 8
[ "$(vip_holder)" = "$OTHER" ] || { echo "XATO: qaytgan $H VIP'ni tortib oldi (nopreempt)"; exit 1; }
[ "$(vip_health)" = ok ] || { echo "XATO: VIP orqali API javob bermadi"; exit 1; }
echo "   $H qaytdi — zaxira (VIP $OTHER da qoldi)"

echo "== T lahza, keyin qo'shimcha faollik"
# Vaqt va soni bitta so'rovda (PostgreSQL soati — tiklash ham shu soat bo'yicha).
TC="$(sql "SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS.US') || '+00|' || count(*) FROM vault_audit")"
T="${TC%%|*}"
C1="${TC##*|}"
echo "   T=$T audit=$C1"
sleep 2
"${DC[@]}" run --rm --no-deps -T --entrypoint sh loadgen -c \
  "mpay-load run --dir /var/lib/mpay/state --server https://lb:8443 --cards 20 --concurrency 4 --duration 5 >/dev/null" \
  2>/dev/null
C2="$(sql "SELECT count(*) FROM vault_audit")"
echo "   keyin audit=$C2"
[ "$C2" -gt "$C1" ] || { echo "XATO: qo'shimcha faollik audit'ga tushmadi"; exit 1; }
# Shield almashinuvidan keyingi yuk (provisioning + avtorizatsiya) yangi yetakchida — mahalliy zaxirasiz.
sleep 12
DEG2="$(prom_q 'sum(mpay_shield_degraded_total)')"
echo "   SHIELD_DEGRADED keyingi yukdan keyin: ${DEG2:-0} (o'tishdan keyin ${DEG1:-0})"
[ "${DEG2:-0}" = "${DEG1:-0}" ] || { echo "XATO: yangi Shield yetakchisi bilan ham mahalliy zaxiraga tushildi"; exit 1; }

echo "== shifrlangan zaxira (B2) va tiklash"
bash "$D/backup.sh" "$BK2" | tail -1
if head -c 512 "$BK2"/*/mpay.dump.age | grep -qa "PGDMP"; then echo "XATO: dump shifrlanmagan"; exit 1; fi
bash "$D/restore.sh" "$BK2"/* --verify

echo "== PITR: B1 + B2 WAL → T"
PITR="$(bash "$D/pitr-restore.sh" "$BK1"/* "$BK2"/* "$T")"
echo "$PITR" | sed 's/^/   /'
rows="$(echo "$PITR" | sed -n 's/^pitr_audit_rows=//p')"
[ "$rows" = "$C1" ] || { echo "XATO: PITR audit=$rows, kutilgan $C1 (T lahzadagi)"; exit 1; }
echo "$PITR" | grep -q "audit zanjiri to'g'ri" || { echo "XATO: PITR audit zanjiri"; exit 1; }

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
