from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CategoryBreakdownItem(BaseModel):
    category_id: str
    category_name: str
    amount: Decimal
    percent: float


class DailyCashFlowItem(BaseModel):
    date: date
    income: Decimal
    expense: Decimal
    net: Decimal


class ReportSummary(BaseModel):
    start_date: date
    end_date: date
    total_income: Decimal
    total_expense: Decimal
    net: Decimal
    by_category: list[CategoryBreakdownItem]
    daily_cash_flow: list[DailyCashFlowItem]
