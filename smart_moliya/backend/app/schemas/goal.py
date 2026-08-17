import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    target_amount: Decimal = Field(gt=0)
    target_date: date
    current_amount: Decimal = Decimal("0")


class GoalContribution(BaseModel):
    amount: Decimal = Field(gt=0)


class GoalRead(ORMModel):
    id: uuid.UUID
    title: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date


class GoalProgress(GoalRead):
    monthly_required_saving: Decimal
    progress_percent: float
