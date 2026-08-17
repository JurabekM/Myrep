import uuid

from pydantic import BaseModel, Field

from app.models.enums import TransactionType
from app.schemas.common import ORMModel


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: TransactionType
    icon: str = "other"


class CategoryRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    type: TransactionType
    icon: str
