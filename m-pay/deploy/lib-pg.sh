# shellcheck shell=bash
# Joriy PostgreSQL yetakchisi (ADR-0027): `postgres` yoki `postgres-replica` — qaysi biri yozish uchun
# ochiq. Almashinuvdan keyin rollar almashadi, shuning uchun zaxira/tiklash skriptlari xizmat nomini
# qattiq yozmaydi. Talab: `DC` massivi (docker compose buyrug'i).
PG_NODES=(postgres postgres-replica)

pg_role() {   # $1 xizmat → f (yetakchi), t (replika) yoki bo'sh (javob yo'q)
  "${DC[@]}" exec -T "$1" psql -U mpay -d mpay -qAtc "SELECT pg_is_in_recovery()" 2>/dev/null | tr -d '\r' || true
}

pg_primary() {
  local s
  for s in "${PG_NODES[@]}"; do
    if [ "$(pg_role "$s")" = f ]; then echo "$s"; return 0; fi
  done
  echo "XATO: PostgreSQL yetakchisi topilmadi" >&2
  return 1
}
