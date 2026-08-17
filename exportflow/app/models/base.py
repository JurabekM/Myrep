"""Declarative base and shared model mixins."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.utils.formatting import now


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base for every ExportFlow model."""


class TimestampMixin:
    """Creation/modification bookkeeping columns."""

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=now, onupdate=now, nullable=False
    )
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ArchiveMixin:
    """Soft delete support - records are archived, never physically removed."""

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    archive_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class IdMixin:
    """Surrogate integer primary key."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
