#!/bin/sh
# HAProxy external-check (ADR-0027): `$3:$4` tuguni yozish uchun ochiq yetakchimi
# (`pg_is_in_recovery() = false`). Replika va javob bermagan tugun — 1 (yo'naltirilmaydi).
# Rol: `replicator` (ma'lumotlarga huquqsiz), parol — Docker secret.
r="$(PGPASSWORD="$(cat /run/secrets/pg_repl_password)" PGCONNECT_TIMEOUT=1 \
  psql -h "$3" -p "$4" -U replicator -d mpay -qAtc "SELECT pg_is_in_recovery()" 2>/dev/null)"
[ "$r" = f ]
