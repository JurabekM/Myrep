import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import BudgetPeriod
from app.schemas.common import ORMModel


class BudgetCreate(BaseModel):
    category_id: uuid.UUID | None = None
    period: BudgetPeriod
    limit_amount: Decimal = Field(gt=0)
    start_date: date


class BudgetRead(ORMModel):
    id: uuid.UUID
    category_id: uuid.UUID | None
    period: BudgetPeriod
    limit_amount: Decimal
    start_date: date


class BudgetStatus(BudgetRead):
    spent: Decimal
    remaining: Decimal
    is_over_limit: bool
