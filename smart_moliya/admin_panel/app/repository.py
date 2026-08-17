"""Admin panel ma'lumot qatlami.

`AdminRepository` - interfeys (testlarda fake bilan almashtiriladi),
`SqlAdminRepository` - haqiqiy PostgreSQL implementatsiyasi (asosiy backend bilan
bir xil bazaga ulanadi, lekin ORM modellarini import qilmasdan to'g'ridan-to'g'ri
SQL bilan ishlaydi - ikki xizmat orasida kod bog'liqligi yo'q).
"""

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings


class AdminRepository(ABC):
    @abstractmethod
    async def get_dashboard_stats(self) -> dict[str, Any]: ...

    @abstractmethod
    async def list_users(self, limit: int = 100) -> list[dict]: ...

    @abstractmethod
    async def set_user_active(self, user_id: str, is_active: bool) -> None: ...

    @abstractmethod
    async def list_transactions(self, limit: int = 100) -> list[dict]: ...

    @abstractmethod
    async def find_suspicious_transactions(self, limit: int = 50) -> list[dict]: ...

    @abstractmethod
    async def get_daily_active_users(self, days: int = 14) -> list[dict]: ...

    @abstractmethod
    async def send_notification(self, user_id: str | None, title: str, body: str) -> int:
        """user_id None bo'lsa - barcha faol foydalanuvchilarga. Nechta yuborilgani qaytadi."""


class SqlAdminRepository(AdminRepository):
    def __init__(self, engine: AsyncEngine):
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def get_dashboard_stats(self) -> dict[str, Any]:
        async with self._session_factory() as session:
            users_total = (await session.execute(text("SELECT COUNT(*) FROM users"))).scalar() or 0
            users_active = (
                await session.execute(text("SELECT COUNT(*) FROM users WHERE is_active"))
            ).scalar() or 0
            txn_total = (await session.execute(text("SELECT COUNT(*) FROM transactions"))).scalar() or 0
            volume = (
                await session.execute(
                    text("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'EXPENSE'")
                )
            ).scalar() or 0
            mau = (
                await session.execute(
                    text(
                        "SELECT COUNT(DISTINCT user_id) FROM transactions "
                        "WHERE occurred_at >= NOW() - INTERVAL '30 days'"
                    )
                )
            ).scalar() or 0

        return {
            "users_total": users_total,
            "users_active": users_active,
            "transactions_total": txn_total,
            "expense_volume": float(volume),
            "monthly_active_users": mau,
        }

    async def list_users(self, limit: int = 100) -> list[dict]:
        async with self._session_factory() as session:
            rows = await session.execute(
                text(
                    "SELECT id, phone, email, full_name, auth_provider, is_active, created_at "
                    "FROM users ORDER BY created_at DESC LIMIT :limit"
                ),
                {"limit": limit},
            )
            return [dict(row) for row in rows.mappings()]

    async def set_user_active(self, user_id: str, is_active: bool) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("UPDATE users SET is_active = :is_active WHERE id = :user_id"),
                {"is_active": is_active, "user_id": user_id},
            )
            await session.commit()

    async def list_transactions(self, limit: int = 100) -> list[dict]:
        async with self._session_factory() as session:
            rows = await session.execute(
                text(
                    "SELECT t.id, t.user_id, u.phone, t.type, t.amount, t.currency, t.note, t.occurred_at "
                    "FROM transactions t JOIN users u ON u.id = t.user_id "
                    "ORDER BY t.occurred_at DESC LIMIT :limit"
                ),
                {"limit": limit},
            )
            return [dict(row) for row in rows.mappings()]

    async def find_suspicious_transactions(self, limit: int = 50) -> list[dict]:
        """Fraud detection: foydalanuvchi+kategoriya o'rtachasidan 2.5+ sigma chetlangan xarajatlar."""
        async with self._session_factory() as session:
            rows = await session.execute(
                text(
                    """
                    WITH stats AS (
                        SELECT user_id, category_id,
                               AVG(amount) AS avg_amount,
                               STDDEV_POP(amount) AS std_amount,
                               COUNT(*) AS txn_count
                        FROM transactions
                        WHERE type = 'EXPENSE'
                        GROUP BY user_id, category_id
                    )
                    SELECT t.id, t.user_id, u.phone, t.amount, t.currency, t.note, t.occurred_at,
                           ROUND(((t.amount - s.avg_amount) / s.std_amount)::numeric, 1) AS z_score
                    FROM transactions t
                    JOIN stats s ON s.user_id = t.user_id
                        AND s.category_id IS NOT DISTINCT FROM t.category_id
                    JOIN users u ON u.id = t.user_id
                    WHERE t.type = 'EXPENSE'
                      AND s.txn_count >= 3
                      AND s.std_amount > 0
                      AND (t.amount - s.avg_amount) / s.std_amount > 2.5
                    ORDER BY t.occurred_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            return [dict(row) for row in rows.mappings()]

    async def get_daily_active_users(self, days: int = 14) -> list[dict]:
        async with self._session_factory() as session:
            rows = await session.execute(
                text(
                    "SELECT DATE(occurred_at) AS day, COUNT(DISTINCT user_id) AS active_users "
                    "FROM transactions WHERE occurred_at >= NOW() - (:days || ' days')::interval "
                    "GROUP BY DATE(occurred_at) ORDER BY day"
                ),
                {"days": str(days)},
            )
            return [dict(row) for row in rows.mappings()]

    async def send_notification(self, user_id: str | None, title: str, body: str) -> int:
        async with self._session_factory() as session:
            if user_id:
                result = await session.execute(
                    text(
                        "INSERT INTO notifications (id, user_id, type, title, payload, is_read) "
                        "VALUES (gen_random_uuid(), :user_id, 'ADMIN_MESSAGE', :title, :body, false)"
                    ),
                    {"user_id": user_id, "title": title, "body": body},
                )
                count = result.rowcount
            else:
                result = await session.execute(
                    text(
                        "INSERT INTO notifications (id, user_id, type, title, payload, is_read) "
                        "SELECT gen_random_uuid(), id, 'ADMIN_MESSAGE', :title, :body, false "
                        "FROM users WHERE is_active"
                    ),
                    {"title": title, "body": body},
                )
                count = result.rowcount
            await session.commit()
            return count or 0


_engine: AsyncEngine | None = None
_repository: SqlAdminRepository | None = None


def get_repository() -> AdminRepository:
    global _engine, _repository
    if _repository is None:
        _engine = create_async_engine(settings.DATABASE_URL)
        _repository = SqlAdminRepository(_engine)
    return _repository
