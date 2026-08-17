"""Generic repository built on top of a SQLAlchemy session."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.utils.formatting import now

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """CRUD helper shared by every concrete repository.

    The repository never commits; transaction boundaries belong to the service
    layer (``session_scope``).
    """

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    # ------------------------------------------------------------------ read
    def get(self, entity_id: int) -> ModelT | None:
        """Return a record by primary key, or ``None``."""
        return self.session.get(self.model, entity_id)

    def base_query(self, include_archived: bool = False) -> Select:
        """Start a select statement, hiding archived rows by default."""
        stmt = select(self.model)
        if not include_archived and hasattr(self.model, "is_archived"):
            stmt = stmt.where(self.model.is_archived.is_(False))
        return stmt

    def list(
        self,
        include_archived: bool = False,
        order_by: Any | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelT]:
        """Return records with optional ordering and pagination."""
        stmt = self.base_query(include_archived)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, "id"):
            stmt = stmt.order_by(self.model.id.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).unique())

    def count(self, include_archived: bool = False) -> int:
        """Count records matching the default visibility filter."""
        stmt = select(func.count()).select_from(self.model)
        if not include_archived and hasattr(self.model, "is_archived"):
            stmt = stmt.where(self.model.is_archived.is_(False))
        return int(self.session.scalar(stmt) or 0)

    def find_by(self, **filters: Any) -> list[ModelT]:
        """Return every record matching simple equality filters."""
        stmt = self.base_query()
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        return list(self.session.scalars(stmt).unique())

    def first_by(self, **filters: Any) -> ModelT | None:
        """Return the first record matching simple equality filters."""
        results = self.find_by(**filters)
        return results[0] if results else None

    # ----------------------------------------------------------------- write
    def add(self, entity: ModelT) -> ModelT:
        """Stage a new record for insertion and flush to obtain its id."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def create(self, **values: Any) -> ModelT:
        """Instantiate and stage a new record from keyword values."""
        entity = self.model(**values)
        return self.add(entity)

    def update(self, entity: ModelT, **values: Any) -> ModelT:
        """Apply attribute updates, ignoring unknown keys."""
        for key, value in values.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        self.session.flush()
        return entity

    def archive(self, entity: ModelT, reason: str | None = None) -> ModelT:
        """Soft delete a record; falls back to a hard delete when unsupported."""
        if hasattr(entity, "is_archived"):
            entity.is_archived = True
            entity.archived_at = now()
            if reason and hasattr(entity, "archive_reason"):
                entity.archive_reason = reason
            self.session.flush()
            return entity
        self.session.delete(entity)
        self.session.flush()
        return entity

    def restore(self, entity: ModelT) -> ModelT:
        """Undo a soft delete."""
        if hasattr(entity, "is_archived"):
            entity.is_archived = False
            entity.archived_at = None
            self.session.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        """Physically remove a record (used only for child rows)."""
        self.session.delete(entity)
        self.session.flush()
