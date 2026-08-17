import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentProviderCode, PaymentStatus
from app.schemas.common import ORMModel


class PaymentCreate(BaseModel):
    wallet_id: uuid.UUID
    provider: PaymentProviderCode
    amount: Decimal = Field(gt=0)
    return_url: str = "smartmoliya://payment-result"


class PaymentRead(ORMModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    provider: PaymentProviderCode
    amount: Decimal
    currency: str
    status: PaymentStatus
    checkout_url: str | None


class PaymentWebhook(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal
    signature: str
