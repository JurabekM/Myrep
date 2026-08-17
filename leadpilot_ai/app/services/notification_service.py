"""Notification centre: in-app alerts for operators and managers."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models.enums import NotificationLevel
from app.models.operations import Notification
from app.utils.dates import now

logger = logging.getLogger(__name__)


def push(
    session: Session,
    *,
    title: str,
    body: str = "",
    level: str = NotificationLevel.INFO,
    category: str = "general",
    user_id: int | None = None,
    lead_id: int | None = None,
    conversation_id: int | None = None,
) -> Notification:
    """Create a notification inside an existing transaction."""
    notification = Notification(
        user_id=user_id,
        lead_id=lead_id,
        conversation_id=conversation_id,
        level=level,
        title=title[:200],
        body=body[:2000],
        category=category,
        created_at=now(),
    )
    session.add(notification)
    session.flush()
    return notification


def notify(
    *,
    title: str,
    body: str = "",
    level: str = NotificationLevel.INFO,
    category: str = "general",
    user_id: int | None = None,
    lead_id: int | None = None,
) -> None:
    """Create a notification in its own transaction."""
    with session_scope() as session:
        push(
            session,
            title=title,
            body=body,
            level=level,
            category=category,
            user_id=user_id,
            lead_id=lead_id,
        )


def list_notifications(
    *, user_id: int | None = None, only_unread: bool = False, limit: int = 100
) -> list[Notification]:
    """Notifications visible to a user (personal + broadcast)."""
    with session_scope() as session:
        stmt = select(Notification)
        if user_id is not None:
            stmt = stmt.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
        if only_unread:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        return list(session.execute(stmt).scalars().all())


def unread_count(user_id: int | None = None) -> int:
    """Number of unread notifications for the top bar badge."""
    with session_scope() as session:
        stmt = select(func.count(Notification.id)).where(Notification.is_read.is_(False))
        if user_id is not None:
            stmt = stmt.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
        return int(session.execute(stmt).scalar_one())


def mark_read(notification_ids: list[int]) -> None:
    """Mark specific notifications as read."""
    with session_scope() as session:
        for notification_id in notification_ids:
            notification = session.get(Notification, notification_id)
            if notification is not None:
                notification.is_read = True


def mark_all_read(user_id: int | None = None) -> int:
    """Mark every visible notification as read; returns how many were updated."""
    with session_scope() as session:
        stmt = select(Notification).where(Notification.is_read.is_(False))
        if user_id is not None:
            stmt = stmt.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
        rows = list(session.execute(stmt).scalars().all())
        for notification in rows:
            notification.is_read = True
        return len(rows)
