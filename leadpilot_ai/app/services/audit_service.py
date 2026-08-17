"""Audit logging: every important action is recorded with before/after values."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system import AuditLog
from app.utils.dates import now

logger = logging.getLogger(__name__)


def record(
    session: Session,
    *,
    action: str,
    entity_type: str = "",
    entity_id: int | None = None,
    entity_label: str = "",
    old_value: Any = "",
    new_value: Any = "",
    detail: str = "",
    user_id: int | None = None,
    username: str = "",
) -> AuditLog:
    """Append one entry to the audit log (never raises)."""
    entry = AuditLog(
        user_id=user_id,
        username=username or "",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label[:200],
        old_value=str(old_value)[:2000],
        new_value=str(new_value)[:2000],
        detail=detail[:2000],
        created_at=now(),
    )
    session.add(entry)
    session.flush()
    logger.debug("Audit: %s %s#%s by %s", action, entity_type, entity_id, username or "system")
    return entry


def search(
    session: Session,
    *,
    query: str = "",
    action: str = "",
    entity_type: str = "",
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[AuditLog]:
    """Filtered audit log listing, newest first."""
    stmt = select(AuditLog)
    if query:
        pattern = f"%{query.lower()}%"
        stmt = stmt.where(
            AuditLog.entity_label.ilike(pattern)
            | AuditLog.detail.ilike(pattern)
            | AuditLog.username.ilike(pattern)
        )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)
    return list(session.execute(stmt).scalars().all())


def distinct_actions(session: Session) -> list[str]:
    """All action codes present in the log (for the filter combo)."""
    rows = session.execute(select(AuditLog.action).distinct().order_by(AuditLog.action)).all()
    return [row[0] for row in rows]
