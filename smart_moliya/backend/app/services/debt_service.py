import uuid

from app.models.debt import Debt
from app.repositories.debt_repository import DebtRepository
from app.schemas.debt import DebtCreate
from app.services.exceptions import NotFoundError


class DebtService:
    def __init__(self, debt_repository: DebtRepository):
        self.debt_repository = debt_repository

    async def create_debt(self, user_id: uuid.UUID, data: DebtCreate) -> Debt:
        debt = Debt(
            user_id=user_id,
            direction=data.direction,
            counterparty=data.counterparty,
            amount=data.amount,
            due_date=data.due_date,
        )
        debt = await self.debt_repository.add(debt)
        await self.debt_repository.commit()
        return debt

    async def list_debts(self, user_id: uuid.UUID) -> list[Debt]:
        return await self.debt_repository.list_by_user(user_id)

    async def mark_settled(self, user_id: uuid.UUID, debt_id: uuid.UUID) -> Debt:
        debt = await self.debt_repository.get(debt_id)
        if debt is None or debt.user_id != user_id:
            raise NotFoundError("Qarz topilmadi")
        debt.is_settled = True
        await self.debt_repository.commit()
        return debt
