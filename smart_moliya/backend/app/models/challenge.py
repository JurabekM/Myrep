import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ChallengePeriod, ChallengeTargetType


class Challenge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Weekly/Monthly Saving Challenge katalogi - global, foydalanuvchilar qo'shiladi."""

    __tablename__ = "challenges"

    code: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(500))
    period: Mapped[ChallengePeriod] = mapped_column(Enum(ChallengePeriod, name="challenge_period"))
    target_type: Mapped[ChallengeTargetType] = mapped_column(
        Enum(ChallengeTargetType, name="challenge_target_type")
    )
    target_value: Mapped[float] = mapped_column(Numeric(18, 2))
    xp_reward: Mapped[int] = mapped_column(default=100)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)


class UserChallenge(Base, UUIDPrimaryKeyMixin):
    """Foydalanuvchining challenge'ga qo'shilishi va progressi."""

    __tablename__ = "user_challenges"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    challenge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("challenges.id"), index=True)
    progress_value: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    challenge: Mapped["Challenge"] = relationship()
