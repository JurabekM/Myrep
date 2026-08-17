"""Generic repository built on top of a SQLAlchemy session.

Repositories own *querying*; they never commit — the surrounding service opens
a transaction with :func:`app.database.session.session_scope`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """CRUD helpers for a single ORM model."""

    model: type[T]

    def __init__(self, session: Session) -> None:
        self.session = session

    # -- read --------------------------------------------------------------- #
    def get(self, entity_id: int) -> T | None:
        """Return a row by primary key or ``None``."""
        return self.session.get(self.model, entity_id)

    def get_or_raise(self, entity_id: int) -> T:
        """Return a row by primary key, raising ``LookupError`` when missing."""
        obj = self.get(entity_id)
        if obj is None:
            raise LookupError(f"{self.model.__name__} #{entity_id} not found")
        return obj

    def list(
        self,
        *,
        filters: Iterable[Any] = (),
        order_by: Any = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[T]:
        """Return rows matching ``filters``."""
        stmt = select(self.model)
        for condition in filters:
            stmt = stmt.where(condition)
        if not include_archived and hasattr(self.model, "is_archived"):
            stmt = stmt.where(self.model.is_archived.is_(False))  # type: ignore[attr-defined]
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def count(self, *, filters: Iterable[Any] = (), include_archived: bool = False) -> int:
        """Count rows matching ``filters``."""
        stmt = select(func.count()).select_from(self.model)
        for condition in filters:
            stmt = stmt.where(condition)
        if not include_archived and hasattr(self.model, "is_archived"):
            stmt = stmt.where(self.model.is_archived.is_(False))  # type: ignore[attr-defined]
        return int(self.session.scalar(stmt) or 0)

    def exists(self, *conditions: Any) -> bool:
        """True when at least one row matches ``conditions``."""
        stmt = select(func.count()).select_from(self.model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return bool(self.session.scalar(stmt))

    # -- write -------------------------------------------------------------- #
    def add(self, obj: T) -> T:
        """Stage a new row."""
        self.session.add(obj)
        self.session.flush()
        return obj

    def create(self, **values: Any) -> T:
        """Instantiate and stage a new row."""
        return self.add(self.model(**values))

    def update(self, obj: T, **values: Any) -> T:
        """Apply ``values`` to ``obj``."""
        for key, value in values.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        self.session.flush()
        return obj

    def archive(self, obj: T, archived: bool = True) -> T:
        """Soft-delete (or restore) a row."""
        if hasattr(obj, "is_archived"):
            obj.is_archived = archived  # type: ignore[attr-defined]
            self.session.flush()
        return obj

    def delete(self, obj: T) -> None:
        """Hard delete — reserved for rows with no historical value."""
        self.session.delete(obj)
        self.session.flush()

    def bulk_add(self, objects: Sequence[T]) -> None:
        """Stage several rows at once."""
        self.session.add_all(list(objects))
        self.session.flush()
