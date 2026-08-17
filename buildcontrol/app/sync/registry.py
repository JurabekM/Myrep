"""Which entities replicate, and how their rows are serialised for the wire.

A row travels as a plain JSON dictionary. Local integer primary keys are never
transmitted — every reference is expressed with the target row's ``uid``, so the
same logical record can carry different local ids on each installation.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.entities import (
    Attachment,
    AuditLog,
    CompanySettings,
    Counterparty,
    DailySiteLog,
    EstimateItem,
    EstimateSection,
    EstimateVersion,
    Expense,
    Material,
    Payment,
    Project,
    ProjectMember,
    PurchaseOrder,
    PurchaseRequest,
    RefItem,
    Role,
    SupplierQuote,
    User,
    WarehouseTransaction,
    WorkStage,
)

#: Replicated entities in dependency order — parents first, so a pulled batch
#: applies cleanly in a single pass most of the time.
SYNC_ENTITIES: list[type[Base]] = [
    Role,
    User,
    RefItem,
    CompanySettings,
    Counterparty,
    Material,
    Project,
    ProjectMember,
    EstimateVersion,
    EstimateSection,
    EstimateItem,
    PurchaseRequest,
    SupplierQuote,
    PurchaseOrder,
    WarehouseTransaction,
    WorkStage,
    DailySiteLog,
    Expense,
    Payment,
    Attachment,
    AuditLog,
]

#: Entity name (the ORM class name) -> model class.
ENTITY_BY_NAME: dict[str, type[Base]] = {model.__name__: model for model in SYNC_ENTITIES}
#: Table name -> model class, used to resolve foreign keys.
ENTITY_BY_TABLE: dict[str, type[Base]] = {model.__tablename__: model for model in SYNC_ENTITIES}
#: Apply priority (lower first).
ENTITY_ORDER: dict[str, int] = {model.__name__: i for i, model in enumerate(SYNC_ENTITIES)}

#: Columns that never travel: local identity and bookkeeping.
SKIPPED_COLUMNS = {"id"}


def is_syncable(obj: Any) -> bool:
    """True when ``obj`` is an instance of a replicated entity."""
    return type(obj) in _SYNCABLE_TYPES or type(obj).__mro__[0] in _SYNCABLE_TYPES


def entity_name(obj: Any) -> str:
    """Return the wire name of ``obj``'s entity.

    Polymorphic subclasses (``Supplier``, ``Contractor``) replicate under their
    single-table base name; the ``kind`` column carries the distinction.
    """
    model = type(obj)
    while model.__name__ not in ENTITY_BY_NAME and model.__bases__:
        model = model.__bases__[0]
    return model.__name__


def _syncable_types() -> set[type]:
    types: set[type] = set()
    for model in SYNC_ENTITIES:
        types.add(model)
        for subclass in model.__subclasses__():
            types.add(subclass)
    return types


_SYNCABLE_TYPES = _syncable_types()


def foreign_key_targets(model: type[Base]) -> dict[str, type[Base]]:
    """Return ``{column_name: target_model}`` for the model's foreign keys."""
    result: dict[str, type[Base]] = {}
    for column in model.__table__.columns:
        for fk in column.foreign_keys:
            target = ENTITY_BY_TABLE.get(fk.column.table.name)
            if target is not None:
                result[column.name] = target
    return result


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #


def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"__dt__": value.isoformat()}
    if isinstance(value, date):
        return {"__d__": value.isoformat()}
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if "__dt__" in value:
            return datetime.fromisoformat(value["__dt__"])
        if "__d__" in value:
            return date.fromisoformat(value["__d__"])
    return value


class UnresolvedReference(Exception):
    """Raised while applying a change whose parent row has not arrived yet."""


def serialise(session: Session, obj: Any) -> dict:
    """Turn an ORM instance into a transport payload."""
    model = ENTITY_BY_NAME[entity_name(obj)]
    fks = foreign_key_targets(model)
    payload: dict[str, Any] = {}
    for column in model.__table__.columns:
        name = column.name
        if name in SKIPPED_COLUMNS:
            continue
        value = getattr(obj, name, None)
        if name in fks:
            payload[name] = _ref_uid(session, fks[name], value)
        else:
            payload[name] = _encode(value)
    return payload


def _ref_uid(session: Session, target: type[Base], local_id: int | None) -> str | None:
    """Translate a local foreign key into the target row's uid."""
    if local_id is None:
        return None
    row = session.get(target, local_id)
    return getattr(row, "uid", None) if row is not None else None


def deserialise(session: Session, model: type[Base], payload: dict) -> dict:
    """Turn a transport payload into column values for this installation."""
    fks = foreign_key_targets(model)
    values: dict[str, Any] = {}
    for name, raw in payload.items():
        if name in SKIPPED_COLUMNS or name not in model.__table__.columns:
            continue
        if name in fks:
            values[name] = _local_id(session, fks[name], raw, name)
        else:
            values[name] = _decode(raw)
    return values


def _local_id(session: Session, target: type[Base], uid: str | None, column: str) -> int | None:
    """Translate an incoming uid into this installation's local id.

    Falls back to the alias table so references to a row that merged under a
    different uid on this device still resolve.
    """
    if not uid:
        return None
    row = session.query(target).filter(target.uid == uid).one_or_none()
    if row is None:
        alias = resolve_alias(session, target.__name__, uid)
        if alias:
            row = session.query(target).filter(target.uid == alias).one_or_none()
    if row is None:
        raise UnresolvedReference(f"{target.__name__}.uid={uid} (for column {column})")
    return row.id


def resolve_alias(session: Session, entity: str, foreign_uid: str) -> str | None:
    """Return the local uid registered for ``foreign_uid``, if any."""
    from app.sync.models import SyncUidAlias

    return session.scalar(
        select(SyncUidAlias.local_uid).where(
            SyncUidAlias.entity == entity, SyncUidAlias.foreign_uid == foreign_uid
        )
    )
