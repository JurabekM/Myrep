import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import DebtDirection
from app.schemas.common import ORMModel


class DebtCreate(BaseModel):
    direction: DebtDirection
    counterparty: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    due_date: date


class DebtRead(ORMModel):
    id: uuid.UUID
    direction: DebtDirection
    counterparty: str
    amount: Decimal
    due_date: date
    is_settled: bool
