import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class WalletCreate(BaseModel):
    id: uuid.UUID | None = None  # mobil klient offline-first uchun oldindan UUID generatsiya qilishi mumkin
    name: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    is_shared: bool = False


class WalletUpdate(BaseModel):
    name: str | None = None
    is_shared: bool | None = None


class WalletRead(ORMModel):
    id: uuid.UUID
    name: str
    currency: str
    balance: Decimal
    is_shared: bool
    version: int
