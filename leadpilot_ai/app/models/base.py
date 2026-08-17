"""Declarative base and shared mixins for all ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.utils.dates import now


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` columns in Asia/Tashkent local time."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now, onupdate=now, nullable=False
    )


class SoftDeleteMixin:
    """Adds archive flags; records are never physically deleted."""

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class IdMixin:
    """Integer surrogate primary key."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
