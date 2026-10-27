"""Server testlari: haqiqiy PostgreSQL 16 (testcontainers) + Alembic migratsiyalari.

- `ZANJIR_TEST_DATABASE_URL` berilsa — shu baza ishlatiladi (masalan, lokal klaster), aks holda Docker konteyner.
- Image: `ZANJIR_TEST_PG_IMAGE` (standart — Docker Hub limitlaridan qochish uchun ECR ko'zgusi).
- Image: `ZANJIR_TEST_PG_IMAGE` (standart — ECR ko'zgusi, Docker Hub limitlaridan qochish uchun).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from tests.support.api import Api
from zanjir_server.config import Argon2Params, Settings
from zanjir_server.main import create_app
from zanjir_server.middleware import RateLimiter

PG_IMAGE = os.environ.get("ZANJIR_TEST_PG_IMAGE", "public.ecr.aws/docker/library/postgres:16-alpine")


def migrate(url: str, target: str = "head", *, down: bool = False) -> None:
    cfg = Config("alembic.ini")
    cfg.attributes["url"] = url
    (command.downgrade if down else command.upgrade)(cfg, target)


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    url = os.environ.get("ZANJIR_TEST_DATABASE_URL")
    if url:
        migrate(url)
        yield url
        return
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(PG_IMAGE, driver="asyncpg") as pg:
        url = pg.get_connection_url()
        migrate(url)
        yield url


APP_ROLE_PASSWORD = "zanjir-api-test"  # noqa: S105 — faqat test konteyneri


@pytest.fixture(scope="session")
def app_url(pg_url: str) -> str:
    """Ilova ulanadigan imtiyozsiz login roli (prod'dagi `zanjir_api` kabi): faqat `zanjir_app` a'zosi.

    Barcha API testlari shu rol bilan ishlaydi — kod RLS'ni chetlab o'tadigan yo'lga tayanmasligini isbotlaydi.
    """
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def setup() -> None:
        engine = create_async_engine(pg_url)
        async with engine.begin() as c:
            await c.execute(
                text(
                    "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zanjir_api_test') THEN "
                    f"CREATE ROLE zanjir_api_test LOGIN PASSWORD '{APP_ROLE_PASSWORD}' NOSUPERUSER NOBYPASSRLS; "
                    "END IF; END $$"
                )
            )
            await c.execute(text("GRANT zanjir_app TO zanjir_api_test"))
        await engine.dispose()

    asyncio.run(setup())
    scheme, rest = pg_url.split("://", 1)
    host = rest.split("@", 1)[1]
    return f"{scheme}://zanjir_api_test:{APP_ROLE_PASSWORD}@{host}"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 27, 8, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw: float) -> None:
        self.now += timedelta(**kw)


@pytest.fixture
def clock() -> Clock:
    return Clock()


def make_settings(pg_url: str, **over: object) -> Settings:
    base: dict[str, object] = {
        "database_url": SecretStr(pg_url),
        "jwt_secret": SecretStr("t" * 48),
        "registration_open": True,
        "argon2": Argon2Params(time_cost=1, memory_kib=1024, parallelism=1),
        "rate_limit_auth_per_minute": 10_000,
        "rate_limit_default_per_minute": 10_000,
        "log_level": "WARNING",
    }
    base.update(over)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture
async def api(app_url: str, clock: Clock) -> AsyncIterator[Api]:
    app = create_app(make_settings(app_url), clock=clock, rate_limiter=RateLimiter())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield Api(client, app)
    await app.state.ctx.db.dispose()
