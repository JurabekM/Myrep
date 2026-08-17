from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class TransactionBase(BaseModel):
    amount: float
    type: str # INCOME or EXPENSE
    description: Optional[str] = None
    wallet_id: UUID
    category_id: Optional[UUID] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: UUID
    date: datetime
    is_ai_categorized: bool
    
    class Config:
        orm_mode = True
