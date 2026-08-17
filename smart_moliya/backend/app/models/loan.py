import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Loan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "loans"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    principal: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_rate: Mapped[float] = mapped_column(Numeric(5, 2))  # yillik foiz, %
    due_date: Mapped[date] = mapped_column(Date)
    penalty_rate_per_day: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    owner: Mapped["User"] = relationship(back_populates="loans")

    def calculate_penalty(self, today: date) -> float:
        overdue_days = (today - self.due_date).days
        if overdue_days <= 0:
            return 0.0
        return float(self.principal) * float(self.penalty_rate_per_day) / 100 * overdue_days
