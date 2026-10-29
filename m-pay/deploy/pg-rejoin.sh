#!/usr/bin/env bash
# Eski yetakchini yangi yetakchining replikasi qilish (ADR-0027):
#
#   bash deploy/pg-rejoin.sh <xizmat>     # masalan: postgres
#
# Xizmat to'xtatiladi, uning ma'lumot hajmi **o'chiriladi** (eski timeline — yangi yetakchi bilan
# mos emas) va qayta ishga tushiriladi: `pg-node.sh` bo'sh papkada yetakchidan `pg_basebackup` oladi.
# WAL arxivi (umumiy hajm) va boshqa tugun tegilmaydi. Yetakchi ishlab turishi shart.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
DC=(docker compose -f "$HERE/docker-compose.yml")
export MSYS_NO_PATHCONV=1
# shellcheck source=lib-pg.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib-pg.sh"
SVC="${1:?xizmat nomi kerak (postgres yoki postgres-replica)}"
case " ${PG_NODES[*]} " in *" $SVC "*) ;; *) echo "XATO: $SVC — PostgreSQL tuguni emas" >&2; exit 2 ;; esac

PRIMARY="$(pg_primary)"
[ "$PRIMARY" != "$SVC" ] || { echo "XATO: $SVC hozir yetakchi — uni qayta qo'shib bo'lmaydi" >&2; exit 1; }

cid="$("${DC[@]}" ps -a -q "$SVC")"
[ -n "$cid" ] || { echo "XATO: $SVC konteyneri yo'q" >&2; exit 1; }
vol="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$cid")"
[ -n "$vol" ] || { echo "XATO: $SVC ma'lumot hajmi topilmadi" >&2; exit 1; }

echo "== $SVC to'xtatilmoqda, hajm $vol o'chiriladi (yetakchi: $PRIMARY)"
"${DC[@]}" rm -s -f "$SVC" >/dev/null
docker volume rm "$vol" >/dev/null
echo "== $SVC qayta ishga tushmoqda ($PRIMARY dan nusxa)"
"${DC[@]}" up -d --no-deps "$SVC" >/dev/null
ok=""
# Tekshiruv qo'shilgan tugunning o'zida: yetakchidagi pg_stat_replication da o'chirilgan eski konteynerning
# walsender yozuvi (wal_sender_timeout gacha) "streaming" bo'lib qoladi — u yangi tugun ulanganini isbotlamaydi.
for _ in $(seq 1 120); do
  s="$("${DC[@]}" exec -T "$SVC" psql -U mpay -d mpay -qAtc \
    "SELECT pg_is_in_recovery()::text || ':' || coalesce((SELECT status FROM pg_stat_wal_receiver), '')" \
    2>/dev/null | tr -d '\r' || true)"
  [ "$s" = "true:streaming" ] && { ok=1; break; }
  sleep 1
done
[ -n "$ok" ] || { "${DC[@]}" logs --tail 30 "$SVC" >&2; echo "XATO: $SVC replikatsiyaga ulanmadi" >&2; exit 1; }
echo "qayta qo'shildi: $SVC — $PRIMARY ning replikasi (streaming)"
