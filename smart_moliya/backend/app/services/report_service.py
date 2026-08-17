import uuid
from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal

from app.models.enums import TransactionType
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.report import CategoryBreakdownItem, DailyCashFlowItem, ReportSummary


class ReportService:
    def __init__(self, transaction_repository: TransactionRepository, category_repository: CategoryRepository):
        self.transaction_repository = transaction_repository
        self.category_repository = category_repository

    async def get_summary(self, user_id: uuid.UUID, start_date: date, end_date: date) -> ReportSummary:
        transactions = await self.transaction_repository.list_between(
            user_id,
            datetime.combine(start_date, time.min, tzinfo=timezone.utc),
            datetime.combine(end_date, time.max, tzinfo=timezone.utc),
        )
        categories = await self.category_repository.list_for_user(user_id)
        category_names = {str(c.id): c.name for c in categories}

        total_income = Decimal("0")
        total_expense = Decimal("0")
        by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        by_day: dict[date, dict[str, Decimal]] = defaultdict(lambda: {"income": Decimal("0"), "expense": Decimal("0")})

        for txn in transactions:
            amount = Decimal(txn.amount)
            day = txn.occurred_at.date()

            if txn.type == TransactionType.INCOME:
                total_income += amount
                by_day[day]["income"] += amount
            elif txn.type == TransactionType.EXPENSE:
                total_expense += amount
                by_day[day]["expense"] += amount
                category_key = str(txn.category_id) if txn.category_id else "other"
                by_category[category_key] += amount

        category_items = [
            CategoryBreakdownItem(
                category_id=category_id,
                category_name=category_names.get(category_id, "Boshqa"),
                amount=amount,
                percent=round(float(amount / total_expense * 100), 2) if total_expense > 0 else 0.0,
            )
            for category_id, amount in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
        ]

        daily_items = [
            DailyCashFlowItem(
                date=day,
                income=values["income"],
                expense=values["expense"],
                net=values["income"] - values["expense"],
            )
            for day, values in sorted(by_day.items())
        ]

        return ReportSummary(
            start_date=start_date,
            end_date=end_date,
            total_income=total_income,
            total_expense=total_expense,
            net=total_income - total_expense,
            by_category=category_items,
            daily_cash_flow=daily_items,
        )
