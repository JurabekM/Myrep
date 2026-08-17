"""
Generic Repository Module
=========================

Implements the **Repository Pattern** using SQLAlchemy 2.0-style queries.
:class:`BaseRepository` provides a complete, reusable CRUD layer that every
domain repository can inherit from, eliminating boilerplate while keeping
all database access behind a clean, testable interface.

Features:
    * Paginated ``get_all`` with dynamic filters and ordering.
    * Rich filter operators: ``eq``, ``ne``, ``gt``, ``lt``, ``gte``,
      ``lte``, ``like``, ``in_``, ``between``.
    * Full-text ``search`` across multiple columns.
    * Soft-delete by default; hard-delete available when needed.
    * Bulk create and bulk update operations.
    * All operations are wrapped with consistent error handling.

Usage::

    class UserRepository(BaseRepository[User]):
        def __init__(self, session_factory):
            super().__init__(session_factory, User)

    repo = UserRepository(engine.get_session)
    user, total = repo.get_all(page=1, per_page=25)
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Callable, Generic, TypeVar

from sqlalchemy import func, inspect, or_, select
from sqlalchemy.orm import Session

from src.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic CRUD repository for any SQLAlchemy model.

    All public methods acquire a session from ``session_factory``, perform
    the operation, and release the session.  Exceptions are caught and
    re-raised as :class:`~src.core.exceptions.DatabaseError`.

    Type Parameters:
        T: The SQLAlchemy model class this repository manages.

    Attributes:
        session_factory: A callable (typically a context-manager factory)
            that yields a :class:`sqlalchemy.orm.Session`.
        model_class: The concrete SQLAlchemy model class.
    """

    # Supported filter operators and their SQLAlchemy equivalents.
    _FILTER_OPERATORS: dict[str, str] = {
        "eq": "__eq__",
        "ne": "__ne__",
        "gt": "__gt__",
        "lt": "__lt__",
        "gte": "__ge__",
        "lte": "__le__",
        "like": "like",
        "in_": "in_",
        "between": "between",
    }

    def __init__(
        self,
        session_factory: Callable[..., Any],
        model_class: type[T],
    ) -> None:
        """Initialise the repository.

        Args:
            session_factory: A callable returning a context-managed
                ``Session`` (e.g. ``DatabaseEngine.get_session``).
            model_class: The SQLAlchemy model this repository operates on.
        """
        self.session_factory = session_factory
        self.model_class: type[T] = model_class

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_id(self, id: str) -> T | None:
        """Fetch a single non-deleted record by its primary key.

        Args:
            id: The UUID primary key value.

        Returns:
            The model instance, or ``None`` if not found or soft-deleted.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                stmt = (
                    select(self.model_class)
                    .where(self.model_class.id == id)
                    .where(self.model_class.is_deleted == False)  # noqa: E712
                )
                result = session.execute(stmt).scalar_one_or_none()
                if result is not None:
                    session.expunge(result)
                return result
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to get {self.model_class.__name__} by id={id}: {exc}"
            ) from exc

    def get_all(
        self,
        page: int = 1,
        per_page: int = 50,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
    ) -> tuple[list[T], int]:
        """Return a paginated, optionally filtered and ordered result set.

        Soft-deleted records are excluded by default.

        Args:
            page: 1-based page number.
            per_page: Maximum records per page.
            filters: A dictionary of ``{field_name: value}`` or
                ``{field_name: {"op": operator, "value": ...}}``.
                See :attr:`_FILTER_OPERATORS` for supported operators.
            order_by: Column name to sort by.  Prefix with ``-`` for
                descending order (e.g. ``"-created_at"``).

        Returns:
            A 2-tuple of ``(items, total_count)``.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                base = select(self.model_class).where(
                    self.model_class.is_deleted == False  # noqa: E712
                )
                base = self._apply_filters(base, filters)

                # Total count (before pagination).
                count_stmt = select(func.count()).select_from(base.subquery())
                total: int = session.execute(count_stmt).scalar() or 0

                # Ordering.
                if order_by:
                    base = self._apply_ordering(base, order_by)
                else:
                    if hasattr(self.model_class, "created_at"):
                        base = base.order_by(self.model_class.created_at.desc())

                # Pagination.
                offset = (max(page, 1) - 1) * per_page
                base = base.offset(offset).limit(per_page)

                items = list(session.execute(base).scalars().all())
                for item in items:
                    session.expunge(item)
                return items, total
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to list {self.model_class.__name__}: {exc}"
            ) from exc

    def exists(self, id: str) -> bool:
        """Check whether a non-deleted record with the given ``id`` exists.

        Args:
            id: The UUID primary key value.

        Returns:
            ``True`` if the record exists and is not soft-deleted.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                stmt = (
                    select(func.count())
                    .select_from(self.model_class)
                    .where(self.model_class.id == id)
                    .where(self.model_class.is_deleted == False)  # noqa: E712
                )
                return (session.execute(stmt).scalar() or 0) > 0
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to check existence for {self.model_class.__name__} "
                f"id={id}: {exc}"
            ) from exc

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Return the total number of non-deleted records matching *filters*.

        Args:
            filters: Optional filter dictionary (same format as ``get_all``).

        Returns:
            The count of matching records.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                base = select(func.count()).select_from(self.model_class).where(
                    self.model_class.is_deleted == False  # noqa: E712
                )
                base = self._apply_filters(base, filters)
                return session.execute(base).scalar() or 0
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to count {self.model_class.__name__}: {exc}"
            ) from exc

    def search(
        self,
        query: str,
        fields: list[str],
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[T], int]:
        """Search for records matching *query* across the given *fields*.

        A case-insensitive ``LIKE`` search is performed on every specified
        column, combined with ``OR``.

        Args:
            query: The search string.
            fields: Column names to search in.
            page: 1-based page number.
            per_page: Maximum records per page.

        Returns:
            A 2-tuple of ``(matching_items, total_count)``.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                conditions = []
                search_term = f"%{query}%"
                for field_name in fields:
                    col = getattr(self.model_class, field_name, None)
                    if col is not None:
                        conditions.append(col.ilike(search_term))

                if not conditions:
                    return [], 0

                base = (
                    select(self.model_class)
                    .where(self.model_class.is_deleted == False)  # noqa: E712
                    .where(or_(*conditions))
                )

                # Total matches.
                count_stmt = select(func.count()).select_from(base.subquery())
                total: int = session.execute(count_stmt).scalar() or 0

                # Paginated results.
                offset = (max(page, 1) - 1) * per_page
                base = base.offset(offset).limit(per_page)

                items = list(session.execute(base).scalars().all())
                for item in items:
                    session.expunge(item)
                return items, total
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to search {self.model_class.__name__}: {exc}"
            ) from exc

    def filter_by(self, **kwargs: Any) -> list[T]:
        """Return all non-deleted records matching the exact field values.

        Args:
            **kwargs: Field-name / value pairs for equality filtering.

        Returns:
            A list of matching model instances.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                stmt = select(self.model_class).where(
                    self.model_class.is_deleted == False  # noqa: E712
                )
                for attr, value in kwargs.items():
                    col = getattr(self.model_class, attr, None)
                    if col is not None:
                        stmt = stmt.where(col == value)

                items = list(session.execute(stmt).scalars().all())
                for item in items:
                    session.expunge(item)
                return items
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to filter {self.model_class.__name__}: {exc}"
            ) from exc

    def first(self, **kwargs: Any) -> T | None:
        """Return the first non-deleted record matching the field values.

        Args:
            **kwargs: Field-name / value pairs for equality filtering.

        Returns:
            The first matching model instance, or ``None``.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                stmt = select(self.model_class).where(
                    self.model_class.is_deleted == False  # noqa: E712
                )
                for attr, value in kwargs.items():
                    col = getattr(self.model_class, attr, None)
                    if col is not None:
                        stmt = stmt.where(col == value)

                result = session.execute(stmt).scalar_one_or_none()
                if result is not None:
                    session.expunge(result)
                return result
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to fetch first {self.model_class.__name__}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create(self, data: dict[str, Any]) -> T:
        """Create a new record from the given data dictionary.

        Args:
            data: Column-name / value mapping for the new record.

        Returns:
            The newly created (and flushed) model instance.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                instance = self.model_class(**data)
                session.add(instance)
                session.flush()
                session.refresh(instance)
                session.expunge(instance)
                return instance
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to create {self.model_class.__name__}: {exc}"
            ) from exc

    def update(self, id: str, data: dict[str, Any]) -> T | None:
        """Update an existing record identified by *id*.

        Only columns present in *data* are modified.

        Args:
            id: The UUID primary key of the record to update.
            data: Column-name / value mapping of fields to update.

        Returns:
            The updated model instance, or ``None`` if not found.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                stmt = (
                    select(self.model_class)
                    .where(self.model_class.id == id)
                    .where(self.model_class.is_deleted == False)  # noqa: E712
                )
                instance = session.execute(stmt).scalar_one_or_none()
                if instance is None:
                    return None

                for key, value in data.items():
                    if hasattr(instance, key) and key != "id":
                        setattr(instance, key, value)

                instance.updated_at = datetime.datetime.utcnow()
                session.flush()
                session.refresh(instance)
                session.expunge(instance)
                return instance
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to update {self.model_class.__name__} id={id}: {exc}"
            ) from exc

    def delete(self, id: str, soft: bool = True) -> bool:
        """Delete a record by its primary key.

        Args:
            id: The UUID primary key of the record.
            soft: If ``True`` (default), perform a logical delete;
                otherwise physically remove the row.

        Returns:
            ``True`` if the record was found and deleted.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        if soft:
            return self._soft_delete(id)
        return self.hard_delete(id)

    def hard_delete(self, id: str) -> bool:
        """Permanently remove a record from the database.

        Args:
            id: The UUID primary key.

        Returns:
            ``True`` if the record was found and removed.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                instance = session.execute(
                    select(self.model_class).where(self.model_class.id == id)
                ).scalar_one_or_none()
                if instance is None:
                    return False
                session.delete(instance)
                session.flush()
                return True
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to hard-delete {self.model_class.__name__} id={id}: {exc}"
            ) from exc

    def bulk_create(self, items: list[dict[str, Any]]) -> list[T]:
        """Create multiple records in a single transaction.

        Args:
            items: A list of column-name / value dictionaries.

        Returns:
            A list of newly created model instances.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            with self.session_factory() as session:
                instances: list[T] = []
                for data in items:
                    instance = self.model_class(**data)
                    session.add(instance)
                    instances.append(instance)

                session.flush()
                for instance in instances:
                    session.refresh(instance)
                for instance in instances:
                    session.expunge(instance)
                return instances
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to bulk-create {self.model_class.__name__}: {exc}"
            ) from exc

    def bulk_update(self, updates: list[dict[str, Any]]) -> int:
        """Update multiple records in a single transaction.

        Each dictionary in *updates* **must** contain an ``id`` key
        identifying the record to update; remaining keys are treated as
        field updates.

        Args:
            updates: A list of dictionaries, each containing ``id`` and
                the fields to update.

        Returns:
            The number of records successfully updated.

        Raises:
            DatabaseError: On any underlying database failure.
        """
        try:
            updated_count = 0
            with self.session_factory() as session:
                for data in updates:
                    record_id = data.get("id")
                    if not record_id:
                        continue

                    instance = session.execute(
                        select(self.model_class)
                        .where(self.model_class.id == record_id)
                        .where(
                            self.model_class.is_deleted == False  # noqa: E712
                        )
                    ).scalar_one_or_none()

                    if instance is None:
                        continue

                    for key, value in data.items():
                        if key != "id" and hasattr(instance, key):
                            setattr(instance, key, value)

                    instance.updated_at = datetime.datetime.utcnow()
                    updated_count += 1

                session.flush()
            return updated_count
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to bulk-update {self.model_class.__name__}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _soft_delete(self, id: str) -> bool:
        """Mark a record as logically deleted.

        Args:
            id: The UUID primary key.

        Returns:
            ``True`` if the record was found and marked as deleted.
        """
        try:
            with self.session_factory() as session:
                instance = session.execute(
                    select(self.model_class)
                    .where(self.model_class.id == id)
                    .where(self.model_class.is_deleted == False)  # noqa: E712
                ).scalar_one_or_none()
                if instance is None:
                    return False

                instance.is_deleted = True
                instance.deleted_at = datetime.datetime.utcnow()
                session.flush()
                return True
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to soft-delete {self.model_class.__name__} id={id}: {exc}"
            ) from exc

    def _apply_filters(self, stmt: Any, filters: dict[str, Any] | None) -> Any:
        """Apply dynamic filter conditions to a query statement.

        Supports both simple equality (``{"field": value}``) and operator
        syntax (``{"field": {"op": "gt", "value": 100}}``).

        Args:
            stmt: The current SQLAlchemy select statement.
            filters: Filter dictionary.

        Returns:
            The modified statement with filter clauses applied.
        """
        if not filters:
            return stmt

        for field_name, condition in filters.items():
            col = getattr(self.model_class, field_name, None)
            if col is None:
                logger.warning(
                    "Ignoring unknown filter field '%s' on %s",
                    field_name,
                    self.model_class.__name__,
                )
                continue

            if isinstance(condition, dict):
                op = condition.get("op", "eq")
                value = condition.get("value")
                stmt = self._apply_operator(stmt, col, op, value)
            else:
                stmt = stmt.where(col == condition)

        return stmt

    def _apply_operator(
        self, stmt: Any, column: Any, op: str, value: Any
    ) -> Any:
        """Apply a single operator clause to the statement.

        Args:
            stmt: The current select statement.
            column: The SQLAlchemy column object.
            op: The operator name (one of :attr:`_FILTER_OPERATORS`).
            value: The comparison value.

        Returns:
            The statement with the operator clause applied.
        """
        if op == "eq":
            stmt = stmt.where(column == value)
        elif op == "ne":
            stmt = stmt.where(column != value)
        elif op == "gt":
            stmt = stmt.where(column > value)
        elif op == "lt":
            stmt = stmt.where(column < value)
        elif op == "gte":
            stmt = stmt.where(column >= value)
        elif op == "lte":
            stmt = stmt.where(column <= value)
        elif op == "like":
            stmt = stmt.where(column.ilike(f"%{value}%"))
        elif op == "in_":
            if isinstance(value, (list, tuple, set)):
                stmt = stmt.where(column.in_(value))
        elif op == "between":
            if isinstance(value, (list, tuple)) and len(value) == 2:
                stmt = stmt.where(column.between(value[0], value[1]))
        else:
            logger.warning("Unsupported filter operator: %s", op)

        return stmt

    @staticmethod
    def _apply_ordering(stmt: Any, order_by: str) -> Any:
        """Apply ordering to a select statement.

        A leading ``-`` indicates descending order.

        Args:
            stmt: The current select statement.
            order_by: Column name, optionally prefixed with ``-``.

        Returns:
            The ordered statement.
        """
        if order_by.startswith("-"):
            field = order_by[1:]
            return stmt.order_by(getattr(stmt.froms[0].c, field, None).desc())
        return stmt.order_by(getattr(stmt.froms[0].c, order_by, None))
