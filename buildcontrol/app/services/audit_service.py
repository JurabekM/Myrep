"""Audit trail writer."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


class Action:
    """Stable audit action codes (localized through ``audit.<code>``)."""

    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ARCHIVE = "archive"
    APPROVE = "approve"
    REJECT = "reject"
    PAYMENT = "payment"
    STOCK = "stock"
    BACKUP = "backup"


def log(
    session: Session,
    *,
    user: User | None,
    action: str,
    entity_type: str = "",
    entity_id: int | None = None,
    project_id: int | None = None,
    description: str = "",
    old_value: str = "",
    new_value: str = "",
) -> AuditLog:
    """Append an entry to the audit trail (does not commit)."""
    entry = AuditLog(
        ts=datetime.now(),
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        description=description,
        old_value=str(old_value or ""),
        new_value=str(new_value or ""),
    )
    session.add(entry)
    session.flush()
    return entry


def diff_text(before: dict, after: dict, fields: list[str]) -> tuple[str, str]:
    """Return ``(old, new)`` textual snapshots limited to ``fields``."""
    old = "; ".join(f"{f}={before.get(f)}" for f in fields if before.get(f) != after.get(f))
    new = "; ".join(f"{f}={after.get(f)}" for f in fields if before.get(f) != after.get(f))
    return old, new
