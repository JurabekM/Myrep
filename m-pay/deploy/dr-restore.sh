#!/usr/bin/env bash
# Falokatdan tiklash (ADR-0028): host (yoki butun muhit) yo'qolgan — shifrlangan zaxiradan **bo'sh**
# compose muhitini to'liq tiklaydi:
#
#   bash deploy/dr-restore.sh <ZAXIRA_PAPKASI>
#
# 1. holat (konfiguratsiya, sertifikatlar, ML-DSA blob) va SoftHSM tokeni → `state`, `hsm` hajmlari;
# 2. PostgreSQL (yetakchi + replika + `pg` proksisi) → `pg_dump` dan tiklash;
# 3. barcha xizmatlar (bootstrap: migratsiyalar va kalitlar — HSM'da allaqachon bor);
# 4. audit xesh-zanjiri (HSM kaliti bilan) — DB va HSM bir-biriga mos.
#
# Talablar: sirlar (`deploy/secrets/`: HSM PIN'i, DB va Shield parollari) — zaxira bilan birga emas,
# alohida saqlanadi (`TODO(spec):` bankning sirlar ombori / HSM); maxfiy zaxira kaliti
# (MPAY_BACKUP_IDENTITY). Ishlab turgan muhitga — rad (`--replace` uchun `restore.sh`).
# RPO — zaxira vaqti (keyingi WAL yo'q: arxiv ham shu host'da edi). Bosqichlar vaqti chiqariladi (RTO).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
SRC="${1:?zaxira papkasi kerak}"
DC=(docker compose -f "$HERE/docker-compose.yml")
IMG="${MPAY_IMAGE:-mpay-server:local}"
IDENTITY="${MPAY_BACKUP_IDENTITY:-$HERE/secrets/backup_identity}"
export MSYS_NO_PATHCONV=1
# shellcheck source=lib-pg.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib-pg.sh"
[ -f "$IDENTITY" ] || { echo "XATO: maxfiy kalit yo'q: $IDENTITY (MPAY_BACKUP_IDENTITY)" >&2; exit 1; }
for s in hsm_pin pg_password pg_repl_password database_url shield_key sms_token; do
  [ -f "$HERE/secrets/$s" ] || { echo "XATO: sir yo'q: secrets/$s (alohida saqlangan nusxadan)" >&2; exit 1; }
done
if [ -n "$("${DC[@]}" ps -a -q)" ]; then
  echo "XATO: muhit bo'sh emas — falokatdan tiklash faqat bo'sh muhitga (ishlab turganga: restore.sh --replace)" >&2
  exit 1
fi

(cd "$SRC" && sha256sum -c --quiet SHA256SUMS)
echo "== SHA256SUMS to'g'ri ($(sed -n 's/^created_utc=//p' "$SRC/MANIFEST"))"

dec() {   # $1 (.age) → stdout; ochiq ma'lumot diskka yozilmaydi
  docker run --rm -i --user "$(id -u):$(id -g)" -v "$IDENTITY:/run/backup_identity:ro" --entrypoint age "$IMG" \
    -d -i /run/backup_identity < "$1"
}
now() { date +%s; }
T0=$(now)
phase() { echo "   $1: $(( $(now) - $2 )) s"; }

echo "== 1/4 holat va HSM tokeni"
t=$(now)
dec "$SRC/state-hsm.tar.gz.age" | "${DC[@]}" run --rm --no-deps -T --user root --entrypoint sh bootstrap -c \
  'tar -C /var/lib/mpay -xzf - && chown -R mpay:mpay /var/lib/mpay/state /var/lib/mpay/hsm' 2>/dev/null
phase "holat va HSM" "$t"

echo "== 2/4 PostgreSQL (yangi klaster, dump'dan)"
t=$(now)
"${DC[@]}" up -d postgres postgres-replica pg >/dev/null 2>&1
ok=""
for _ in $(seq 1 120); do
  if "${DC[@]}" exec -T pg pg-primary-check - - 127.0.0.1 5432 2>/dev/null; then ok=1; break; fi
  sleep 1
done
[ -n "$ok" ] || { echo "XATO: PostgreSQL yetakchisi ko'tarilmadi" >&2; exit 1; }
PGP="$(pg_primary)"
dec "$SRC/mpay.dump.age" | "${DC[@]}" exec -T "$PGP" pg_restore -U mpay -d mpay --no-owner --exit-on-error
rows="$("${DC[@]}" exec -T "$PGP" psql -U mpay -d mpay -qAtc "SELECT count(*) FROM vault_audit" | tr -d '\r')"
phase "PostgreSQL ($rows audit yozuvi)" "$t"

echo "== 3/4 xizmatlar"
t=$(now)
"${DC[@]}" up -d --no-build >/dev/null 2>&1
ok=""
for _ in $(seq 1 180); do
  h="$("${DC[@]}" ps --format '{{.Service}}={{.Health}}' 2>/dev/null | tr '\n' ' ')"
  if echo "$h" | grep -q "api-1=healthy" && echo "$h" | grep -q "api-2=healthy"; then ok=1; break; fi
  sleep 1
done
[ -n "$ok" ] || { "${DC[@]}" ps; echo "XATO: API instansiyalari sog'lom bo'lmadi" >&2; exit 1; }
phase "xizmatlar (API sog'lom)" "$t"

echo "== 4/4 audit xesh-zanjiri (HSM kaliti bilan)"
t=$(now)
"${DC[@]}" run --rm --no-deps -T --entrypoint mpay-entrypoint bootstrap \
  mpay-server audit-verify --config /var/lib/mpay/state/mpay.toml 2>/dev/null
phase "audit" "$t"
echo "dr_restore_seconds=$(( $(now) - T0 ))"
echo "DR TIKLASH OK"
