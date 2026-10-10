import uuid
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


async def set_db_context(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> None:
    """Joriy tranzaksiya uchun RLS kontekstini o'rnatadi.

    set_config(..., is_local=true) qiymatni faqat shu tranzaksiya davomida saqlaydi,
    shuning uchun commit/rollback'dan keyin u avtomatik tozalanadi.
    """
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant, true), set_config('app.user_id', :user, true)"),
        {"tenant": str(tenant_id) if tenant_id else "", "user": str(user_id) if user_id else ""},
    )
