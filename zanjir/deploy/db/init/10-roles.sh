#!/bin/sh
# PostgreSQL birinchi ishga tushishida (bo'sh volume) — rollar va baza (ADR-0011, ADR-0015):
# zanjir_owner — jadvallar egasi (faqat migratsiya va zaxira), zanjir_api — ilova, faqat zanjir_app a'zosi (RLS majburiy).
set -eu
: "${ZANJIR_OWNER_PASSWORD:?}" "${ZANJIR_API_PASSWORD:?}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v owner_pw="$ZANJIR_OWNER_PASSWORD" -v api_pw="$ZANJIR_API_PASSWORD" <<'SQL'
CREATE ROLE zanjir_owner LOGIN PASSWORD :'owner_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE zanjir_app NOLOGIN NOSUPERUSER NOBYPASSRLS;
GRANT zanjir_app TO zanjir_owner WITH ADMIN OPTION;
CREATE ROLE zanjir_api LOGIN PASSWORD :'api_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
GRANT zanjir_app TO zanjir_api;
CREATE DATABASE zanjir OWNER zanjir_owner;
REVOKE ALL ON DATABASE zanjir FROM PUBLIC;
GRANT CONNECT ON DATABASE zanjir TO zanjir_api;
SQL
