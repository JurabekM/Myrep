"""Generic repository with the CRUD operations shared by every entity."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.utils.dates import now

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """CRUD helper bound to one model class and one session."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get(self, entity_id: int) -> ModelT | None:
        """Fetch by primary key."""
        return self.session.get(self.model, entity_id)

    def get_or_raise(self, entity_id: int) -> ModelT:
        """Fetch by primary key or raise ``LookupError``."""
        entity = self.get(entity_id)
        if entity is None:
            raise LookupError(f"{self.model.__name__} #{entity_id} not found")
        return entity

    def list(
        self,
        *,
        include_archived: bool = False,
        order_by: Any | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filters: Any,
    ) -> list[ModelT]:
        """Return rows matching simple equality filters."""
        stmt = select(self.model)
        if not include_archived and hasattr(self.model, "is_archived"):
            stmt = stmt.where(self.model.is_archived.is_(False))  # type: ignore[attr-defined]
        for field, value in filters.items():
            if value is None:
                continue
            stmt = stmt.where(getattr(self.model, field) == value)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count(self, *, include_archived: bool = False, **filters: Any) -> int:
        """Count rows matching simple equality filters."""
        stmt = select(func.count()).select_from(self.model)
        if not include_archived and hasattr(self.model, "is_archived"):
            stmt = stmt.where(self.model.is_archived.is_(False))  # type: ignore[attr-defined]
        for field, value in filters.items():
            if value is None:
                continue
            stmt = stmt.where(getattr(self.model, field) == value)
        return int(self.session.execute(stmt).scalar_one())

    def add(self, entity: ModelT) -> ModelT:
        """Stage a new entity (flush so the id becomes available)."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def create(self, **values: Any) -> ModelT:
        """Instantiate and stage a new entity."""
        entity = self.model(**values)  # type: ignore[call-arg]
        return self.add(entity)

    def update(self, entity: ModelT, **values: Any) -> ModelT:
        """Apply attribute updates and flush."""
        for field, value in values.items():
            setattr(entity, field, value)
        self.session.flush()
        return entity

    def archive(self, entity: ModelT) -> ModelT:
        """Soft delete: mark as archived instead of removing the row."""
        if hasattr(entity, "is_archived"):
            entity.is_archived = True  # type: ignore[attr-defined]
            entity.archived_at = now()  # type: ignore[attr-defined]
            self.session.flush()
        return entity

    def restore(self, entity: ModelT) -> ModelT:
        """Undo :meth:`archive`."""
        if hasattr(entity, "is_archived"):
            entity.is_archived = False  # type: ignore[attr-defined]
            entity.archived_at = None  # type: ignore[attr-defined]
            self.session.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        """Hard delete. Only used for join rows and test fixtures."""
        self.session.delete(entity)
        self.session.flush()
