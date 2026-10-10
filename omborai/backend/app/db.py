import uuid
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from .config import get_settings

_RLS_SQL = text("SELECT set_config('app.tenant_id', :tenant, true), set_config('app.user_id', :user, true)")


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


def _rls_params(ctx: tuple[uuid.UUID | None, uuid.UUID | None]) -> dict[str, str]:
    tenant_id, user_id = ctx
    return {"tenant": str(tenant_id) if tenant_id else "", "user": str(user_id) if user_id else ""}


@event.listens_for(Session, "after_begin")
def _reapply_rls_context(session: Session, _transaction, connection) -> None:  # type: ignore[no-untyped-def]
    """Har yangi tranzaksiyada RLS kontekstini qayta o'rnatadi.

    set_config(..., is_local=true) commit/rollback'dan keyin tozalanadi. Shu sabab commit'dan keyin
    o'qish (masalan, javob tayyorlash) tenant'siz ishlab, ma'lumotni yashirib qo'yardi.
    """
    ctx = session.info.get("rls")
    if ctx is not None:
        connection.execute(_RLS_SQL, _rls_params(ctx))


async def set_db_context(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> None:
    """Sessiya uchun RLS kontekstini belgilaydi: joriy va keyingi tranzaksiyalarda ishlaydi."""
    session.info["rls"] = (tenant_id, user_id)
    await session.execute(_RLS_SQL, _rls_params((tenant_id, user_id)))
