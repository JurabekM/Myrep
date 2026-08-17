import asyncio
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.enums import TransactionType
from app.services.report_service import ReportService


@dataclass
class FakeTransaction:
    id: uuid.UUID
    type: TransactionType
    amount: Decimal
    occurred_at: datetime
    category_id: uuid.UUID | None = None


@dataclass
class FakeCategory:
    id: uuid.UUID
    name: str


class FakeTransactionRepository:
    def __init__(self, transactions: list[FakeTransaction]):
        self._transactions = transactions

    async def list_between(self, user_id, start, end):
        return [t for t in self._transactions if start <= t.occurred_at <= end]


class FakeCategoryRepository:
    def __init__(self, categories: list[FakeCategory]):
        self._categories = categories

    async def list_for_user(self, user_id):
        return self._categories


def test_report_summary_aggregates_income_expense_and_categories():
    food_category_id = uuid.uuid4()
    user_id = uuid.uuid4()

    transactions = [
        FakeTransaction(
            id=uuid.uuid4(),
            type=TransactionType.INCOME,
            amount=Decimal("3000000"),
            occurred_at=datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc),
        ),
        FakeTransaction(
            id=uuid.uuid4(),
            type=TransactionType.EXPENSE,
            amount=Decimal("200000"),
            occurred_at=datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc),
            category_id=food_category_id,
        ),
        FakeTransaction(
            id=uuid.uuid4(),
            type=TransactionType.EXPENSE,
            amount=Decimal("100000"),
            occurred_at=datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc),
            category_id=food_category_id,
        ),
    ]
    categories = [FakeCategory(id=food_category_id, name="Oziq ovqat")]

    service = ReportService(FakeTransactionRepository(transactions), FakeCategoryRepository(categories))
    summary = asyncio.run(service.get_summary(user_id, date(2026, 7, 1), date(2026, 7, 31)))

    assert summary.total_income == Decimal("3000000")
    assert summary.total_expense == Decimal("300000")
    assert summary.net == Decimal("2700000")
    assert len(summary.by_category) == 1
    assert summary.by_category[0].category_name == "Oziq ovqat"
    assert summary.by_category[0].percent == 100.0
    assert len(summary.daily_cash_flow) == 3


def test_report_summary_with_no_transactions_returns_zeroes():
    service = ReportService(FakeTransactionRepository([]), FakeCategoryRepository([]))
    summary = asyncio.run(service.get_summary(uuid.uuid4(), date(2026, 7, 1), date(2026, 7, 31)))

    assert summary.total_income == Decimal("0")
    assert summary.total_expense == Decimal("0")
    assert summary.by_category == []
    assert summary.daily_cash_flow == []
