import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Goal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "goals"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    target_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    current_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    target_date: Mapped[date] = mapped_column(Date)

    owner: Mapped["User"] = relationship(back_populates="goals")

    def monthly_required_saving(self, today: date) -> float:
        months_left = max(
            1, (self.target_date.year - today.year) * 12 + (self.target_date.month - today.month)
        )
        remaining = float(self.target_amount) - float(self.current_amount)
        return max(0.0, remaining / months_left)
