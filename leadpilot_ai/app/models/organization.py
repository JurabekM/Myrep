"""Company, users, roles, branches and services."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base, IdMixin):
    """A single fine grained capability such as ``lead.assign``."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Permission {self.code}>"


class Role(Base, IdMixin, TimestampMixin):
    """A named bundle of permissions."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    title_uz: Mapped[str] = mapped_column(String(96), default="")
    title_ru: Mapped[str] = mapped_column(String(96), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    users: Mapped[list[User]] = relationship(back_populates="role")

    def permission_codes(self) -> set[str]:
        """Return the permission codes granted by this role."""
        return {p.code for p in self.permissions}


class Company(Base, IdMixin, TimestampMixin):
    """Tenant record. The application currently runs single-company."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(200), default="")
    industry: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_language: Mapped[str] = mapped_column(String(8), default="uz")
    timezone: Mapped[str] = mapped_column(String(48), default="Asia/Tashkent")
    work_start: Mapped[str] = mapped_column(String(5), default="09:00")
    work_end: Mapped[str] = mapped_column(String(5), default="19:00")
    work_days: Mapped[str] = mapped_column(String(32), default="1,2,3,4,5,6")
    currency: Mapped[str] = mapped_column(String(16), default="so'm")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    branches: Mapped[list[Branch]] = relationship(back_populates="company")
    users: Mapped[list[User]] = relationship(back_populates="company")


class Branch(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """Physical location / filial of the company."""

    __tablename__ = "branches"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    work_start: Mapped[str] = mapped_column(String(5), default="09:00")
    work_end: Mapped[str] = mapped_column(String(5), default="19:00")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped[Company] = relationship(back_populates="branches")


class Service(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """Sellable service or product offered by the company."""

    __tablename__ = "services"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(160), default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    price_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    branch: Mapped[Branch | None] = relationship()

    @property
    def price_label(self) -> str:
        """Return the price range as a plain string used by the AI agent."""
        if self.price_max and self.price_max > self.price:
            return f"{int(self.price):,}–{int(self.price_max):,}".replace(",", " ")
        return f"{int(self.price):,}".replace(",", " ")


class User(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """Application user (administrator, manager, operator, analyst, viewer)."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)

    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    language: Mapped[str] = mapped_column(String(8), default="uz")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_operator: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    avatar_color: Mapped[str] = mapped_column(String(16), default="#3B82F6")

    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")
    company: Mapped[Company] = relationship(back_populates="users", lazy="joined")
    branch: Mapped[Branch | None] = relationship(lazy="joined")

    def has_permission(self, code: str) -> bool:
        """Check whether the user's role grants ``code``."""
        return code in self.role.permission_codes()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username} ({self.role.name if self.role else '-'})>"
