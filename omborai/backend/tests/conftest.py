"""Testlar haqiqiy PostgreSQL'da ishlaydi (RLS'ni mock bilan sinab bo'lmaydi).

Kerak: OMBORAI_TEST_ADMIN_URL (superuser, masalan postgres) — test bazasini yaratish uchun.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

ADMIN_URL = os.environ.get("OMBORAI_TEST_ADMIN_URL", "postgresql+asyncpg://postgres@localhost:5432/postgres")
TEST_DB = "omborai_test"
APP_ROLE = "omborai_app"
APP_PASSWORD = os.environ.get("OMBORAI_TEST_APP_PASSWORD", "omborai_app")
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _db_url(base: str, database: str, user: str | None = None, password: str | None = None) -> str:
    # base: postgresql+asyncpg://[user@]host:port/<db>
    prefix, rest = base.split("://", 1)
    base_user, host_part = rest.split("@", 1)
    host_part = host_part.rsplit("/", 1)[0]
    creds = f"{user or base_user}:{password}" if password else (user or base_user)
    return f"{prefix}://{creds}@{host_part}/{database}"


OWNER_URL = _db_url(ADMIN_URL, TEST_DB)
APP_URL = _db_url(ADMIN_URL, TEST_DB, APP_ROLE, APP_PASSWORD)

# Ilova sozlamalari import qilinishidan OLDIN o'rnatiladi
os.environ["OMBORAI_MIGRATION_URL"] = OWNER_URL
os.environ["OMBORAI_DATABASE_URL"] = APP_URL
os.environ["OMBORAI_JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256-ok"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.db import get_engine, get_sessionmaker  # noqa: E402


async def _recreate_database() -> None:
    admin = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
        await conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    await admin.dispose()


async def _set_app_login() -> None:
    admin = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f"ALTER ROLE {APP_ROLE} LOGIN PASSWORD '{APP_PASSWORD}'"))
    await admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    asyncio.run(_recreate_database())
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")  # rol NOLOGIN yaratiladi
    asyncio.run(_set_app_login())  # test uchun LOGIN beriladi


@pytest.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    owner = create_async_engine(OWNER_URL)
    async with owner.begin() as conn:
        await conn.execute(
            text("TRUNCATE refresh_tokens, memberships, stores, users, tenants RESTART IDENTITY CASCADE")
        )
    await owner.dispose()

    # Har test o'z event loop'ida ishlaydi: engine keshini tozalaymiz
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    yield
    await get_engine().dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def owner_url() -> str:
    return OWNER_URL
