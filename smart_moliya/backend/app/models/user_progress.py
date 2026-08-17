import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

XP_PER_LEVEL = 1000


class UserProgress(Base):
    """Har foydalanuvchi uchun bitta yozuv - XP, level, streak (gamification holati)."""

    __tablename__ = "user_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    xp: Mapped[int] = mapped_column(default=0)
    level: Mapped[int] = mapped_column(default=1)
    current_streak: Mapped[int] = mapped_column(default=0)
    longest_streak: Mapped[int] = mapped_column(default=0)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    @staticmethod
    def level_for_xp(xp: int) -> int:
        return xp // XP_PER_LEVEL + 1
