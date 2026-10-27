"""Baza ulanishi va sessiyalar — barcha so'rovlar RLS ostida (ADR-0011).

- `org_session(org_id)` — tranzaksiya ichida `SET LOCAL ROLE zanjir_app` va `app.org_id`: Postgres RLS faqat shu
  tashkilot qatorlarini ko'rsatadi va yozdiradi (kodda `org_id` filtri ham bor, CLAUDE.md 7-qoida).
- `lookup_org(...)` — tashkilot hali noma'lum bo'lgan yo'llar (kirish, refresh, taklif, `/v/{qr_token}`): migratsiyadagi
  `SECURITY DEFINER` funksiya aniq kalit bo'yicha faqat `org_id` qaytaradi; qolgan ish yana `org_session` da.
  Ilova ulanadigan rol (`zanjir_api`) o'zi hech qanday jadvalga huquqqa ega emas.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

APP_ROLE = "zanjir_app"
Lookup = Literal["zanjir_org_of_phone", "zanjir_org_of_refresh", "zanjir_org_of_invite", "zanjir_org_of_qr"]


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True)
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def org_session(self, org_id: str) -> AsyncIterator[AsyncSession]:
        async with self._sessions() as s, s.begin():
            await s.execute(text(f"SET LOCAL ROLE {APP_ROLE}"))
            await s.execute(text("SELECT set_config('app.org_id', :org, true)"), {"org": org_id})
            yield s

    async def lookup_org(self, fn: Lookup, key: str) -> str | None:
        async with self._sessions() as s, s.begin():
            await s.execute(text(f"SET LOCAL ROLE {APP_ROLE}"))
            org: str | None = (await s.execute(text(f"SELECT {fn}(:k)"), {"k": key})).scalar()
            return org

    async def ping(self) -> None:
        async with self.engine.connect() as c:
            await c.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self.engine.dispose()
