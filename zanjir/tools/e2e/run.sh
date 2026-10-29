#!/usr/bin/env bash
# ZANJIR E2E (8-faza, ADR-0012): PostgreSQL 16 + server (uvicorn) + Dart testlari (packages/zanjir_data, `-t e2e`).
#
# Foydalanish (repo ildizidan yoki istalgan joydan):
#   zanjir/tools/e2e/run.sh                 # Docker'da PostgreSQL ko'tariladi
#   ZANJIR_E2E_OWNER_URL=postgresql+asyncpg://user:pw@localhost:5432/db zanjir/tools/e2e/run.sh   # mavjud baza (CI)
# Maxfiy qiymatlar (JWT kaliti, parollar) har ishga tushirishda tasodifiy yaratiladi va hech qayerga yozilmaydi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PG_IMAGE="${ZANJIR_TEST_PG_IMAGE:-postgres:16-alpine}"
PORT="${ZANJIR_E2E_PORT:-18080}"
CONTAINER=""
SERVER_PID=""

cleanup() {
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
  [[ -n "$CONTAINER" ]] && docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

rand() { python3 -c "import secrets; print(secrets.token_hex(${1:-16}))"; }

if [[ -z "${ZANJIR_E2E_OWNER_URL:-}" ]]; then
  PG_PW="$(rand)"
  CONTAINER="zanjir-e2e-$(rand 4)"
  docker run -d --name "$CONTAINER" -e POSTGRES_USER=zanjir_owner -e POSTGRES_PASSWORD="$PG_PW" -e POSTGRES_DB=zanjir \
    -p 127.0.0.1::5432 "$PG_IMAGE" >/dev/null
  PG_PORT="$(docker port "$CONTAINER" 5432/tcp | head -1 | sed 's/.*://')"
  for _ in $(seq 1 60); do
    docker exec "$CONTAINER" pg_isready -U zanjir_owner -d zanjir >/dev/null 2>&1 && break
    sleep 1
  done
  sleep 1
  ZANJIR_E2E_OWNER_URL="postgresql+asyncpg://zanjir_owner:${PG_PW}@127.0.0.1:${PG_PORT}/zanjir"
fi

cd "$ROOT/server"
uv sync --locked --quiet
ZANJIR_DATABASE_URL="$ZANJIR_E2E_OWNER_URL" uv run alembic upgrade head

# Ilova roli: faqat zanjir_app a'zosi (prod'dagi zanjir_api kabi, docs/DEPLOY.md).
API_PW="$(rand)"
ZANJIR_E2E_OWNER_URL="$ZANJIR_E2E_OWNER_URL" API_PW="$API_PW" uv run python - <<'PY'
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main() -> None:
    engine = create_async_engine(os.environ["ZANJIR_E2E_OWNER_URL"])
    async with engine.begin() as c:
        await c.execute(text("DROP ROLE IF EXISTS zanjir_api_e2e"))
        await c.execute(text(f"CREATE ROLE zanjir_api_e2e LOGIN PASSWORD '{os.environ['API_PW']}' NOSUPERUSER NOBYPASSRLS"))
        await c.execute(text("GRANT zanjir_app TO zanjir_api_e2e"))
    await engine.dispose()

asyncio.run(main())
PY
HOSTPART="${ZANJIR_E2E_OWNER_URL#*@}"
export ZANJIR_DATABASE_URL="postgresql+asyncpg://zanjir_api_e2e:${API_PW}@${HOSTPART}"
export ZANJIR_JWT_SECRET="$(rand 32)"
export ZANJIR_REGISTRATION_OPEN=true
export ZANJIR_RATE_LIMIT_AUTH_PER_MINUTE=1000
export ZANJIR_RATE_LIMIT_DEFAULT_PER_MINUTE=100000
export ZANJIR_ARGON2_TIME_COST=1 ZANJIR_ARGON2_MEMORY_KIB=8192 ZANJIR_ARGON2_PARALLELISM=1
export ZANJIR_LOG_LEVEL=WARNING
uv run uvicorn --factory zanjir_server.main:app --host 127.0.0.1 --port "$PORT" --log-level warning &
SERVER_PID=$!
for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${PORT}/readyz" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "http://127.0.0.1:${PORT}/readyz" >/dev/null

cd "$ROOT/packages/zanjir_data"
ZANJIR_E2E_URL="http://127.0.0.1:${PORT}" dart test -P e2e-run test/e2e "$@"
