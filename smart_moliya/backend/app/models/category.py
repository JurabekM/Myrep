import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TransactionType


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "categories"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )  # NULL = tizim standart kategoriyasi
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name="category_type"))
    icon: Mapped[str] = mapped_column(String(50), default="other")

    owner: Mapped[Optional["User"]] = relationship(back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")
