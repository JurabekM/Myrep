from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class WalletBase(BaseModel):
    name: str
    currency: Optional[str] = "UZS"

class WalletCreate(WalletBase):
    pass

class WalletResponse(WalletBase):
    id: UUID
    user_id: UUID
    balance: float
    
    class Config:
        orm_mode = True
