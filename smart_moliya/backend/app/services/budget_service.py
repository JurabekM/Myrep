import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.models.budget import Budget
from app.models.enums import BudgetPeriod, TransactionType
from app.repositories.budget_repository import BudgetRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.budget import BudgetCreate, BudgetStatus


class BudgetService:
    def __init__(self, budget_repository: BudgetRepository, transaction_repository: TransactionRepository):
        self.budget_repository = budget_repository
        self.transaction_repository = transaction_repository

    async def create_budget(self, user_id: uuid.UUID, data: BudgetCreate) -> Budget:
        budget = Budget(
            user_id=user_id,
            category_id=data.category_id,
            period=data.period,
            limit_amount=data.limit_amount,
            start_date=data.start_date,
        )
        budget = await self.budget_repository.add(budget)
        await self.budget_repository.commit()
        return budget

    async def list_with_status(self, user_id: uuid.UUID) -> list[BudgetStatus]:
        budgets = await self.budget_repository.list_by_user(user_id)
        today = date.today()
        results = []
        for budget in budgets:
            period_start = self._period_start(budget.period, today)
            transactions = await self.transaction_repository.list_between(
                user_id,
                datetime.combine(period_start, time.min, tzinfo=timezone.utc),
                datetime.combine(today, time.max, tzinfo=timezone.utc),
            )
            spent = sum(
                Decimal(t.amount)
                for t in transactions
                if t.type == TransactionType.EXPENSE
                and (budget.category_id is None or t.category_id == budget.category_id)
            )
            remaining = Decimal(budget.limit_amount) - spent
            results.append(
                BudgetStatus(
                    id=budget.id,
                    category_id=budget.category_id,
                    period=budget.period,
                    limit_amount=budget.limit_amount,
                    start_date=budget.start_date,
                    spent=spent,
                    remaining=remaining,
                    is_over_limit=remaining < 0,
                )
            )
        return results

    @staticmethod
    def _period_start(period: BudgetPeriod, today: date) -> date:
        if period == BudgetPeriod.DAILY:
            return today
        if period == BudgetPeriod.WEEKLY:
            return today - timedelta(days=today.weekday())
        return today.replace(day=1)
