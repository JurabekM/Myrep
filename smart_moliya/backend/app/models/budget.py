import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BudgetPeriod


class Budget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "budgets"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )  # NULL = umumiy byudjet
    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod, name="budget_period"))
    limit_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    start_date: Mapped[date] = mapped_column(Date)

    owner: Mapped["User"] = relationship(back_populates="budgets")
