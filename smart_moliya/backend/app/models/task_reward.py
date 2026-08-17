import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TaskRewardStatus


class TaskReward(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Family Mode - ota-ona bolaga vazifa/pocket money tayinlaydi."""

    __tablename__ = "task_rewards"

    family_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_groups.id"), index=True)
    assigned_to_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    reward_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    status: Mapped[TaskRewardStatus] = mapped_column(
        Enum(TaskRewardStatus, name="task_reward_status"), default=TaskRewardStatus.PENDING
    )
