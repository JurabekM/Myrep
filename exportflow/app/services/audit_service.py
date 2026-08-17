"""Audit trail writing and querying."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Activity, AuditLog
from app.utils.formatting import now


def record(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    summary: str = "",
    details: dict[str, Any] | None = None,
    user_id: int | None = None,
    username: str | None = None,
) -> AuditLog:
    """Append an entry to the audit log within the caller's transaction."""
    entry = AuditLog(
        at=now(),
        user_id=user_id,
        username=username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary[:400],
        details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
    )
    session.add(entry)
    session.flush()
    return entry


def add_activity(
    session: Session,
    *,
    entity_type: str,
    entity_id: int,
    title: str,
    kind: str = "note",
    body: str | None = None,
    user_id: int | None = None,
) -> Activity:
    """Append a timeline activity for a buyer, lead, quotation or shipment."""
    activity = Activity(
        entity_type=entity_type,
        entity_id=entity_id,
        kind=kind,
        title=title[:300],
        body=body,
        user_id=user_id,
        happened_at=now(),
    )
    session.add(activity)
    session.flush()
    return activity


def timeline(session: Session, entity_type: str, entity_id: int, limit: int = 200) -> list[dict]:
    """Return the activity timeline of one entity, newest first."""
    stmt = (
        select(Activity)
        .where(Activity.entity_type == entity_type, Activity.entity_id == entity_id)
        .order_by(desc(Activity.happened_at), desc(Activity.id))
        .limit(limit)
    )
    rows = session.scalars(stmt).all()
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "body": row.body,
            "happened_at": row.happened_at,
            "user_id": row.user_id,
        }
        for row in rows
    ]


def search(
    session: Session,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    username: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """Query the audit log with optional filters."""
    stmt = select(AuditLog).order_by(desc(AuditLog.at), desc(AuditLog.id)).limit(limit)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if username:
        stmt = stmt.where(AuditLog.username == username)
    return [
        {
            "id": row.id,
            "at": row.at,
            "username": row.username or "-",
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "summary": row.summary,
            "details": row.details,
        }
        for row in session.scalars(stmt).all()
    ]
