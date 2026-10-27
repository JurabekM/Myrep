#!/bin/sh
# Birinchi initdb'da (ADR-0027): replikatsiya roli va pg_hba qatori. Replika `pg_basebackup` bilan
# pg_hba.conf ni ham oladi — almashinuvdan keyin yangi yetakchi ham replikalarni qabul qiladi.
# `replicator` — faqat REPLICATION va LOGIN (ma'lumotlarga huquqi yo'q); `pg` proksisining
# "yetakchimi" tekshiruvi ham shu rol bilan (`SELECT pg_is_in_recovery()`).
set -e
PW="$(cat /run/secrets/pg_repl_password)"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q <<SQL
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '$PW';
SQL
echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
