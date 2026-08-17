import uuid
from datetime import datetime

from sqlalchemy import select

from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    async def list_between(self, user_id: uuid.UUID, start: datetime, end: datetime) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.occurred_at >= start,
                Transaction.occurred_at <= end,
            )
        )
        return list(result.scalars().all())

    async def list_updated_since(self, user_id: uuid.UUID, since_version: int) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(Transaction.user_id == user_id, Transaction.version > since_version)
        )
        return list(result.scalars().all())
