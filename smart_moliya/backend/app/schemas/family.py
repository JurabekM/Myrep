import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import TaskRewardStatus
from app.schemas.common import ORMModel


class FamilyGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FamilyGroupRead(ORMModel):
    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID


class FamilyMemberRead(ORMModel):
    id: uuid.UUID
    full_name: str | None
    phone: str | None


class FamilyGroupWithMembers(BaseModel):
    group: FamilyGroupRead
    members: list[FamilyMemberRead]


class AllowanceRequest(BaseModel):
    child_wallet_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    note: str | None = None


class TaskRewardCreate(BaseModel):
    assigned_to_user_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    reward_amount: Decimal = Field(gt=0)


class TaskRewardApprove(BaseModel):
    wallet_id: uuid.UUID


class TaskRewardRead(ORMModel):
    id: uuid.UUID
    assigned_to_user_id: uuid.UUID
    title: str
    reward_amount: Decimal
    status: TaskRewardStatus
