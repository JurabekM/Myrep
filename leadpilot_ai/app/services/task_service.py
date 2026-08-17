"""Follow-up tasks and the automatic rule engine that keeps leads from being lost."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models.crm import Lead
from app.models.enums import (
    CLOSED_STATUSES,
    ConversationStatus,
    NotificationLevel,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from app.models.enums import (
    Permission as Perm,
)
from app.models.messaging import Conversation
from app.models.operations import Task
from app.services import audit_service, notification_service
from app.services.auth_service import CurrentUser
from app.utils.dates import end_of_day, now, start_of_day

logger = logging.getLogger(__name__)

#: Thresholds of the automatic rule engine, all in minutes.
RULE_FIRST_RESPONSE_MINUTES = 15
RULE_HOT_LEAD_ALERT_MINUTES = 10
RULE_BOOKING_REMINDER_HOURS = 24
RULE_NO_SHOW_FOLLOWUP_HOURS = 2


class TaskError(Exception):
    """Task rule violation (``code`` is an i18n key)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def create_task(
    *,
    title: str,
    lead_id: int | None = None,
    booking_id: int | None = None,
    assignee_id: int | None = None,
    task_type: str = TaskType.OTHER,
    description: str = "",
    due_at: datetime | None = None,
    priority: str = TaskPriority.NORMAL,
    auto_rule: str = "",
    actor: CurrentUser | None = None,
    session: Session | None = None,
) -> Task:
    """Create a task. Rule-generated tasks are deduplicated by ``auto_rule``."""

    def _create(db: Session) -> Task:
        if auto_rule and lead_id:
            existing = (
                db.execute(
                    select(Task).where(
                        Task.lead_id == lead_id,
                        Task.auto_rule == auto_rule,
                        Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS]),
                    )
                )
                .scalars()
                .first()
            )
            if existing is not None:
                return existing
        task = Task(
            lead_id=lead_id,
            booking_id=booking_id,
            assignee_id=assignee_id,
            created_by_id=actor.id if actor else None,
            task_type=task_type,
            title=title[:200],
            description=description,
            due_at=due_at or (now() + timedelta(hours=1)),
            priority=priority,
            auto_rule=auto_rule,
            status=TaskStatus.OPEN,
        )
        db.add(task)
        db.flush()
        notification_service.push(
            db,
            title="Yangi vazifa",
            body=task.title,
            level=(
                NotificationLevel.CRITICAL
                if priority == TaskPriority.CRITICAL
                else NotificationLevel.INFO
            ),
            category="task",
            user_id=assignee_id,
            lead_id=lead_id,
        )
        return task

    if session is not None:
        return _create(session)
    with session_scope() as db:
        return _create(db)


def list_tasks(
    *,
    actor: CurrentUser | None = None,
    statuses: list[str] | None = None,
    assignee_id: int | None = None,
    task_types: list[str] | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    search: str = "",
    only_mine: bool = False,
    limit: int = 500,
) -> list[Task]:
    """Filtered task list."""
    with session_scope() as session:
        stmt = select(Task).where(Task.is_archived.is_(False))
        if statuses:
            stmt = stmt.where(Task.status.in_(statuses))
        if task_types:
            stmt = stmt.where(Task.task_type.in_(task_types))
        if assignee_id:
            stmt = stmt.where(Task.assignee_id == assignee_id)
        elif only_mine and actor is not None:
            stmt = stmt.where(Task.assignee_id == actor.id)
        elif actor is not None and not actor.can(Perm.LEAD_VIEW_ALL):
            stmt = stmt.where(or_(Task.assignee_id == actor.id, Task.assignee_id.is_(None)))
        if due_from:
            stmt = stmt.where(Task.due_at >= due_from)
        if due_to:
            stmt = stmt.where(Task.due_at <= due_to)
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
        stmt = stmt.order_by(Task.due_at.asc().nullslast(), Task.id.desc()).limit(limit)
        return list(session.execute(stmt).scalars().unique().all())


def tasks_for_lead(lead_id: int) -> list[Task]:
    """Tasks linked to one lead."""
    with session_scope() as session:
        stmt = (
            select(Task)
            .where(Task.lead_id == lead_id, Task.is_archived.is_(False))
            .order_by(Task.due_at.asc().nullslast())
        )
        return list(session.execute(stmt).scalars().unique().all())


def complete_task(task_id: int, *, actor: CurrentUser, comment: str = "") -> Task:
    """Mark a task as done."""
    actor.require(Perm.TASK_MANAGE)
    with session_scope() as session:
        task = session.get(Task, task_id)
        if task is None:
            raise TaskError("task_not_found")
        task.status = TaskStatus.DONE
        task.completed_at = now()
        task.result_comment = comment
        audit_service.record(
            session,
            action="task_completed",
            entity_type="task",
            entity_id=task.id,
            entity_label=task.title,
            user_id=actor.id,
            username=actor.username,
        )
        return task


def update_task(
    task_id: int,
    *,
    actor: CurrentUser,
    status: str | None = None,
    assignee_id: int | None = None,
    due_at: datetime | None = None,
    priority: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> Task:
    """Update a task."""
    actor.require(Perm.TASK_MANAGE)
    with session_scope() as session:
        task = session.get(Task, task_id)
        if task is None:
            raise TaskError("task_not_found")
        old_status = task.status
        if status is not None:
            task.status = status
            if status == TaskStatus.DONE:
                task.completed_at = now()
        if assignee_id is not None:
            task.assignee_id = assignee_id
        if due_at is not None:
            task.due_at = due_at
        if priority is not None:
            task.priority = priority
        if title is not None:
            task.title = title[:200]
        if description is not None:
            task.description = description
        session.flush()
        audit_service.record(
            session,
            action="task_updated",
            entity_type="task",
            entity_id=task.id,
            entity_label=task.title,
            old_value=old_status,
            new_value=task.status,
            user_id=actor.id,
            username=actor.username,
        )
        return task


def open_task_count(actor: CurrentUser | None = None) -> int:
    """Number of open tasks visible to the actor (sidebar badge)."""
    return len(
        list_tasks(
            actor=actor,
            statuses=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE],
            limit=1000,
        )
    )


def overdue_tasks(actor: CurrentUser | None = None) -> list[Task]:
    """Tasks whose due date has passed."""
    return [
        task
        for task in list_tasks(
            actor=actor, statuses=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS], limit=1000
        )
        if task.due_at and task.due_at < now()
    ]


# --------------------------------------------------------------------------- #
# Automatic rule engine
# --------------------------------------------------------------------------- #
def run_rules() -> dict[str, int]:
    """Evaluate every automation rule. Returns a counter per rule.

    Rules implemented:

    * lead waiting more than 15 minutes without a reply → task for the operator;
    * hot lead unanswered for 10 minutes → critical alert for the manager;
    * booking within 24 hours → reminder task;
    * missed booking → follow-up task after 2 hours;
    * overdue tasks are flagged.
    """
    counters = {
        "first_response": 0,
        "hot_alert": 0,
        "booking_reminder": 0,
        "no_show": 0,
        "overdue": 0,
    }
    current = now()
    with session_scope() as session:
        # Rule 1 & 2: unanswered conversations
        stmt = select(Conversation).where(
            Conversation.is_archived.is_(False),
            Conversation.status != ConversationStatus.CLOSED,
            Conversation.unread_count > 0,
            Conversation.last_message_at.isnot(None),
        )
        for conversation in session.execute(stmt).scalars().unique().all():
            lead = session.get(Lead, conversation.lead_id)
            if lead is None or lead.status in CLOSED_STATUSES:
                continue
            waiting_minutes = int((current - conversation.last_message_at).total_seconds() // 60)
            if waiting_minutes >= RULE_FIRST_RESPONSE_MINUTES:
                created = create_task(
                    session=session,
                    lead_id=lead.id,
                    assignee_id=lead.owner_id,
                    task_type=TaskType.WRITE_BACK,
                    title=f"Javobsiz lead: {lead.display_name}",
                    description=f"{waiting_minutes} daqiqadan beri javob berilmagan.",
                    due_at=current,
                    priority=TaskPriority.HIGH,
                    auto_rule="first_response_sla",
                )
                if created.created_at >= current - timedelta(seconds=5):
                    counters["first_response"] += 1
            if lead.intent == "hot" and waiting_minutes >= RULE_HOT_LEAD_ALERT_MINUTES:
                notification_service.push(
                    session,
                    title="Issiq lead javobsiz!",
                    body=f"{lead.display_name} — {waiting_minutes} daqiqa",
                    level=NotificationLevel.CRITICAL,
                    category="hot_lead_sla",
                    lead_id=lead.id,
                    conversation_id=conversation.id,
                )
                counters["hot_alert"] += 1

        # Rule 5: overdue tasks
        overdue_stmt = select(Task).where(
            Task.is_archived.is_(False),
            Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS]),
            Task.due_at < current,
        )
        for task in session.execute(overdue_stmt).scalars().unique().all():
            task.status = TaskStatus.OVERDUE
            counters["overdue"] += 1

    # Rules 3 & 4 live in the booking service (they own the booking state)
    from app.services import booking_service

    counters["booking_reminder"] = booking_service.send_reminders(RULE_BOOKING_REMINDER_HOURS)
    counters["no_show"] = booking_service.mark_missed_bookings()
    return counters


def today_agenda(actor: CurrentUser) -> list[Task]:
    """Tasks due today for the current user."""
    return list_tasks(
        actor=actor,
        statuses=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE],
        due_from=start_of_day(now()),
        due_to=end_of_day(now()),
        only_mine=True,
    )
