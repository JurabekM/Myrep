"""
Database Models Module
======================

Defines the SQLAlchemy declarative base and reusable ORM mixins used by all
domain models across the Enterprise ERP platform.

Mixins:
    TimestampMixin: Auto-managed ``created_at`` / ``updated_at`` columns.
    SoftDeleteMixin: Logical deletion with ``is_deleted`` flag and timestamp.
    AuditMixin: Tracks the creating and updating user identifiers.

Classes:
    BaseModel: Abstract base model that composes all mixins and provides a
        UUID primary key, dictionary serialisation, and a developer-friendly
        ``__repr__``.

.. note::
    Concrete domain models (User, Role, Permission, etc.) are defined in
    their respective module packages (e.g. ``src.auth.models``).
"""



import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import DeclarativeBase, declared_attr

from src.core.utils import generate_uuid


# ======================================================================
# Declarative base
# ======================================================================


class Base(DeclarativeBase):
    """Root declarative base for all ORM models in the ERP platform.

    All models should inherit either directly from :class:`Base` or, more
    commonly, from :class:`BaseModel` which bundles frequently-needed
    mixins.
    """

    __allow_unmapped__ = True


# ======================================================================
# Mixins
# ======================================================================


class TimestampMixin:
    """Mixin that adds automatic ``created_at`` and ``updated_at`` columns.

    ``created_at`` is set once when the row is first inserted.
    ``updated_at`` is refreshed on every update.
    """

    created_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
        doc="UTC timestamp of row creation.",
    )
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
        doc="UTC timestamp of last update.",
    )


class SoftDeleteMixin:
    """Mixin that supports logical (soft) deletion.

    Instead of physically removing rows, ``is_deleted`` is set to ``True``
    and ``deleted_at`` records the deletion timestamp.  Queries should
    typically filter on ``is_deleted == False``.
    """

    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Flag indicating logical deletion.",
    )
    deleted_at = Column(
        DateTime,
        nullable=True,
        doc="UTC timestamp when the row was soft-deleted.",
    )


class AuditMixin:
    """Mixin that tracks the user responsible for creating/updating a row.

    The values are stored as plain strings (typically UUIDs) so that
    the mixin remains decoupled from any specific ``User`` model.
    """

    created_by = Column(
        String(36),
        nullable=True,
        doc="Identifier of the user who created the record.",
    )
    updated_by = Column(
        String(36),
        nullable=True,
        doc="Identifier of the user who last updated the record.",
    )


# ======================================================================
# Abstract base model
# ======================================================================


class BaseModel(Base, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """Abstract base model composing all standard mixins.

    Provides:
        * ``id`` — UUID primary key (auto-generated).
        * ``created_at`` / ``updated_at`` — automatic timestamps.
        * ``is_deleted`` / ``deleted_at`` — soft-delete support.
        * ``created_by`` / ``updated_by`` — audit trail.
        * ``to_dict()`` — serialise the instance to a plain dictionary.
        * ``__repr__()`` — developer-friendly string representation.

    All concrete domain models should inherit from this class unless they
    have a compelling reason to opt out of one or more mixins.
    """

    __abstract__ = True

    id = Column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique UUID identifier for the record.",
    )

    @declared_attr
    def __tablename__(cls) -> str:  # noqa: N805 — SQLAlchemy convention
        """Derive the table name from the class name in snake_case.

        For example, ``SalesOrder`` becomes ``sales_order``.
        """
        name = cls.__name__
        # Convert CamelCase to snake_case.
        result: list[str] = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the model instance to a dictionary.

        DateTime values are converted to ISO-8601 strings for JSON
        compatibility.

        Returns:
            A dictionary mapping column names to their current values.
        """
        result: dict[str, Any] = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def __repr__(self) -> str:
        """Return a concise string representation of the model instance."""
        return f"<{self.__class__.__name__}(id={self.id!r})>"
