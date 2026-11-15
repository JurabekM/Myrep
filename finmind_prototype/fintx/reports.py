"""Asosiy moliyaviy hisob-kitoblar.

Sof funksiyalar: bazaga tegmaydi, faqat tranzaksiyalar ro'yxatidan hisoblaydi.
Summalar tiyinda (int), ulushlar `Decimal` bilan — `float` ishlatilmaydi.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .transactions import Transaction
from .validation import KIND_EXPENSE, KIND_INCOME

_ONE_DECIMAL = Decimal("0.1")


@dataclass(frozen=True)
class CategoryShare:
    category: str
    amount_minor: int
    percent: Decimal  # shu turdagi jami summadan ulush, %


@dataclass(frozen=True)
class MonthSummary:
    month: str  # YYYY-MM
    income_minor: int
    expense_minor: int

    @property
    def net_minor(self) -> int:
        return self.income_minor - self.expense_minor


@dataclass(frozen=True)
class Report:
    count: int
    income_minor: int
    expense_minor: int
    # Jamg'arma ulushi = (daromad − xarajat) / daromad; daromad bo'lmasa — None.
    savings_rate: Decimal | None
    average_expense_minor: int | None
    largest_expense: Transaction | None
    expense_by_category: tuple[CategoryShare, ...]
    income_by_category: tuple[CategoryShare, ...]
    monthly: tuple[MonthSummary, ...]

    @property
    def balance_minor(self) -> int:
        return self.income_minor - self.expense_minor


def percent(part: int, whole: int) -> Decimal | None:
    """`part` ning `whole` dagi ulushi, bir kasr xonasigacha. Bo'luvchi nol bo'lsa — None."""
    if whole == 0:
        return None
    return (Decimal(part) * 100 / Decimal(whole)).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP)


def _shares(totals: dict[str, int]) -> tuple[CategoryShare, ...]:
    whole = sum(totals.values())
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return tuple(
        CategoryShare(category, amount, percent(amount, whole) or Decimal(0))
        for category, amount in ordered
    )


def build_report(transactions: Iterable[Transaction]) -> Report:
    income = expense = count = expense_count = 0
    by_category: dict[str, dict[str, int]] = {
        KIND_INCOME: defaultdict(int),
        KIND_EXPENSE: defaultdict(int),
    }
    months: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    largest: Transaction | None = None

    for tx in transactions:
        count += 1
        month = months[tx.occurred_on.strftime("%Y-%m")]
        by_category[tx.kind][tx.category] += tx.amount_minor
        if tx.kind == KIND_INCOME:
            income += tx.amount_minor
            month[0] += tx.amount_minor
        else:
            expense += tx.amount_minor
            expense_count += 1
            month[1] += tx.amount_minor
            if largest is None or tx.amount_minor > largest.amount_minor:
                largest = tx

    average_expense = None
    if expense_count:
        # Yaxlitlash: yarim tiyin yuqoriga.
        average_expense = (2 * expense + expense_count) // (2 * expense_count)

    return Report(
        count=count,
        income_minor=income,
        expense_minor=expense,
        savings_rate=percent(income - expense, income),
        average_expense_minor=average_expense,
        largest_expense=largest,
        expense_by_category=_shares(by_category[KIND_EXPENSE]),
        income_by_category=_shares(by_category[KIND_INCOME]),
        monthly=tuple(
            MonthSummary(month, values[0], values[1])
            for month, values in sorted(months.items(), reverse=True)
        ),
    )
