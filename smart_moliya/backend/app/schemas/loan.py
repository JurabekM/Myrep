import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LoanCreate(BaseModel):
    principal: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(ge=0)
    due_date: date
    penalty_rate_per_day: Decimal = Decimal("0")


class LoanRead(ORMModel):
    id: uuid.UUID
    principal: Decimal
    interest_rate: Decimal
    due_date: date
    penalty_rate_per_day: Decimal


class LoanStatus(LoanRead):
    current_penalty: Decimal
    is_overdue: bool
