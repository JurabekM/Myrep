import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DebtDirection


class Debt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "debts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    direction: Mapped[DebtDirection] = mapped_column(Enum(DebtDirection, name="debt_direction"))
    counterparty: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    due_date: Mapped[date] = mapped_column(Date)
    is_settled: Mapped[bool] = mapped_column(default=False)

    owner: Mapped["User"] = relationship(back_populates="debts")
