#!/bin/sh
# Birinchi ishga tushirishda ilova roli yaratiladi. U superuser EMAS, shuning uchun RLS unga ta'sir qiladi.
# Migratsiya bu rolni yaratmaydi (IF NOT EXISTS), faqat unga ruxsat beradi.
set -eu

: "${OMBORAI_APP_PASSWORD:?OMBORAI_APP_PASSWORD o'rnatilmagan}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE omborai_app LOGIN PASSWORD '${OMBORAI_APP_PASSWORD}' NOSUPERUSER NOBYPASSRLS;
EOSQL
