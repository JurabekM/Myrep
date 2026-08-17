import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Card(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Karta - faqat oxirgi 4 raqam saqlanadi (PCI doirasidan tashqarida qolish uchun)."""

    __tablename__ = "cards"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    bank_code: Mapped[str] = mapped_column(String(50))  # asaka, nbu, ipoteka, kapitalbank, ...
    last4: Mapped[str] = mapped_column(String(4))
    card_type: Mapped[str] = mapped_column(String(20), default="debit")

    owner: Mapped["User"] = relationship(back_populates="cards")
