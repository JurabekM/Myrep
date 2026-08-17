import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import SyncStatus, TransactionSource, TransactionType
from app.schemas.common import ORMModel


class TransactionCreate(BaseModel):
    id: uuid.UUID | None = None  # mobil klient offline-first uchun oldindan UUID generatsiya qilishi mumkin
    wallet_id: uuid.UUID
    category_id: uuid.UUID | None = None
    card_id: uuid.UUID | None = None
    type: TransactionType
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    note: str | None = None
    source: TransactionSource = TransactionSource.MANUAL
    occurred_at: datetime


class TransactionRead(ORMModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    category_id: uuid.UUID | None
    type: TransactionType
    amount: Decimal
    currency: str
    note: str | None
    source: TransactionSource
    occurred_at: datetime
    sync_status: SyncStatus
    version: int
