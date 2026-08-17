import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.transaction import TransactionRead
from app.schemas.wallet import WalletRead


class SyncPushTransaction(BaseModel):
    client_id: uuid.UUID  # mobil qurilmada yaratilgan lokal ID
    wallet_id: uuid.UUID
    category_id: uuid.UUID | None = None
    type: str
    amount: float
    currency: str = "UZS"
    note: str | None = None
    source: str = "manual"
    occurred_at: datetime
    version: int = 1


class SyncPushRequest(BaseModel):
    transactions: list[SyncPushTransaction] = []


class SyncPushResult(BaseModel):
    client_id: uuid.UUID
    server_id: uuid.UUID
    version: int


class SyncPushResponse(BaseModel):
    accepted: list[SyncPushResult]


class SyncPullResponse(BaseModel):
    since_version: int
    server_version: int
    wallets: list[WalletRead]
    transactions: list[TransactionRead]
