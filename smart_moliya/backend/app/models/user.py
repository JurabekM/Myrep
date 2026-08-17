import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuthProvider, Language


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider"), default=AuthProvider.PHONE
    )
    language: Mapped[Language] = mapped_column(Enum(Language, name="language"), default=Language.UZ)
    is_active: Mapped[bool] = mapped_column(default=True)

    family_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_groups.id"), nullable=True
    )
    family_group: Mapped[Optional["FamilyGroup"]] = relationship(
        back_populates="members", foreign_keys=[family_group_id]
    )

    wallets: Mapped[list["Wallet"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    cards: Mapped[list["Card"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    goals: Mapped[list["Goal"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    loans: Mapped[list["Loan"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    debts: Mapped[list["Debt"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    investments: Mapped[list["Investment"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[list["Achievement"]] = relationship(back_populates="user", cascade="all, delete-orphan")
