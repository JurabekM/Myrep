"""Declarative base and shared column mixins."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase


def new_uid() -> str:
    """Return a globally unique row identifier."""
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    """Base class for every ORM model."""

    def as_dict(self) -> dict:
        """Return a plain ``{column: value}`` mapping of this row."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TimestampMixin:
    """Adds creation / modification timestamps."""

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class ArchivableMixin:
    """Soft-delete support: rows are archived instead of being removed."""

    is_archived = Column(Boolean, default=False, nullable=False, index=True)


class PKMixin:
    """Integer surrogate primary key."""

    id = Column(Integer, primary_key=True, autoincrement=True)


class SyncMixin:
    """Makes a table replicable across installations.

    ``uid`` is the identity shared by every device (the integer primary key is
    local only and differs per machine). ``sync_ts`` carries the logical write
    time used for last-write-wins conflict resolution.
    """

    uid = Column(String(32), unique=True, index=True, default=new_uid, nullable=False)
    sync_ts = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
