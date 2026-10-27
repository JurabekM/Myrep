"""Alembic muhiti (async). URL: `config.attributes["url"]` (testlar) yoki `ZANJIR_DATABASE_URL`."""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from zanjir_server.db.models import Base

config = context.config
target_metadata = Base.metadata


def _do_run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run() -> None:
    url = config.attributes.get("url") or os.environ["ZANJIR_DATABASE_URL"]
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        await conn.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline (SQL) rejimi qo'llanilmaydi")
asyncio.run(_run())
