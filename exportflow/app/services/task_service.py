"""Tasks and the automatic follow-up rule engine.

Business rules implemented here:

* quotation sent + 3 days without a reply  -> follow-up task for the manager;
* sample sent + 5 days                     -> ask the buyer for feedback;
* quotation expiry in 7 days               -> alert the responsible manager;
* certificate expiry in 60/30/7 days       -> task for the catalog manager.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Certificate, Lead, Quotation, Task, User
from app.services.auth_service import CurrentUser
from app.utils.enums import ROLE_CATALOG_MANAGER
from app.utils.errors import NotFoundError
from app.utils.formatting import now, today

FOLLOW_UP_AFTER_QUOTATION_DAYS = 3
FEEDBACK_AFTER_SAMPLE_DAYS = 5
QUOTATION_EXPIRY_ALERT_DAYS = 7
CERTIFICATE_ALERT_DAYS = (60, 30, 7)


def _task_exists(session: Session, rule_code: str, entity_type: str, entity_id: int) -> bool:
    return bool(
        session.scalar(
            select(Task.id).where(
                Task.rule_code == rule_code,
                Task.entity_type == entity_type,
                Task.entity_id == entity_id,
                Task.is_archived.is_(False),
            )
        )
    )


def create_task(
    session: Session,
    *,
    title: str,
    rule_code: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    buyer_id: int | None = None,
    lead_id: int | None = None,
    assignee_id: int | None = None,
    due_date: dt.date | None = None,
    priority: str = "normal",
    description: str | None = None,
) -> Task:
    """Create a task, skipping duplicates when a rule code is supplied."""
    if (
        rule_code
        and entity_type
        and entity_id
        and _task_exists(session, rule_code, entity_type, entity_id)
    ):
        existing = session.scalar(
            select(Task).where(
                Task.rule_code == rule_code,
                Task.entity_type == entity_type,
                Task.entity_id == entity_id,
                Task.is_archived.is_(False),
            )
        )
        return existing
    task = Task(
        title=title[:300],
        description=description,
        rule_code=rule_code,
        entity_type=entity_type,
        entity_id=entity_id,
        buyer_id=buyer_id,
        lead_id=lead_id,
        assignee_id=assignee_id,
        due_date=due_date or today(),
        priority=priority,
        status="open",
    )
    session.add(task)
    session.flush()
    return task


def apply_stage_rules(session: Session, lead: Lead) -> list[Task]:
    """Create the stage-driven follow-up tasks for a lead."""
    created: list[Task] = []
    if lead.status == "quotation_sent":
        created.append(
            create_task(
                session,
                title=f"Follow up on quotation - {lead.title}",
                rule_code="lead.quotation_followup",
                entity_type="lead",
                entity_id=lead.id,
                buyer_id=lead.buyer_id,
                lead_id=lead.id,
                assignee_id=lead.manager_id,
                due_date=today() + dt.timedelta(days=FOLLOW_UP_AFTER_QUOTATION_DAYS),
                priority="high",
                description="No reply expected after 3 days - contact the buyer.",
            )
        )
    elif lead.status == "sample_sent":
        created.append(
            create_task(
                session,
                title=f"Ask for sample feedback - {lead.title}",
                rule_code="lead.sample_feedback",
                entity_type="lead",
                entity_id=lead.id,
                buyer_id=lead.buyer_id,
                lead_id=lead.id,
                assignee_id=lead.manager_id,
                due_date=today() + dt.timedelta(days=FEEDBACK_AFTER_SAMPLE_DAYS),
                priority="normal",
            )
        )
    elif lead.status == "contract_signed":
        created.append(
            create_task(
                session,
                title=f"Prepare shipment for {lead.title}",
                rule_code="lead.prepare_shipment",
                entity_type="lead",
                entity_id=lead.id,
                buyer_id=lead.buyer_id,
                lead_id=lead.id,
                due_date=today() + dt.timedelta(days=3),
                priority="high",
            )
        )
    return [task for task in created if task is not None]


def run_follow_up_rules(session: Session) -> dict[str, int]:
    """Scan the database and materialise every pending follow-up task."""
    counters = {"quotation_followup": 0, "quotation_expiry": 0, "certificate_expiry": 0}
    right_now = now()

    # 1) Quotations sent more than N days ago without a reply.
    cutoff = right_now - dt.timedelta(days=FOLLOW_UP_AFTER_QUOTATION_DAYS)
    quotations = (
        session.scalars(
            select(Quotation).where(
                Quotation.is_archived.is_(False),
                Quotation.status.in_(("sent", "viewed")),
                Quotation.sent_at.is_not(None),
                Quotation.replied_at.is_(None),
            )
        )
        .unique()
        .all()
    )
    for quotation in quotations:
        sent_at = quotation.sent_at
        if sent_at is not None and sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=right_now.tzinfo)
        if sent_at is None or sent_at > cutoff:
            continue
        if not _task_exists(session, "quotation.followup", "quotation", quotation.id):
            create_task(
                session,
                title=f"No reply to quotation {quotation.number} - follow up",
                rule_code="quotation.followup",
                entity_type="quotation",
                entity_id=quotation.id,
                buyer_id=quotation.buyer_id,
                lead_id=quotation.lead_id,
                assignee_id=quotation.manager_id,
                due_date=today(),
                priority="high",
            )
            counters["quotation_followup"] += 1

    # 2) Quotations expiring soon.
    horizon = today() + dt.timedelta(days=QUOTATION_EXPIRY_ALERT_DAYS)
    expiring = (
        session.scalars(
            select(Quotation).where(
                Quotation.is_archived.is_(False),
                Quotation.valid_until.is_not(None),
                Quotation.valid_until <= horizon,
                Quotation.valid_until >= today(),
                Quotation.status.not_in(("accepted", "rejected", "cancelled", "expired")),
            )
        )
        .unique()
        .all()
    )
    for quotation in expiring:
        if not _task_exists(session, "quotation.expiry", "quotation", quotation.id):
            create_task(
                session,
                title=f"Quotation {quotation.number} expires on {quotation.valid_until}",
                rule_code="quotation.expiry",
                entity_type="quotation",
                entity_id=quotation.id,
                buyer_id=quotation.buyer_id,
                lead_id=quotation.lead_id,
                assignee_id=quotation.manager_id,
                due_date=quotation.valid_until,
                priority="high",
            )
            counters["quotation_expiry"] += 1

    # 3) Certificates expiring in 60 / 30 / 7 days.
    catalog_manager = session.scalar(
        select(User)
        .join(User.role)
        .where(User.is_archived.is_(False))
        .where(User.role.has(code=ROLE_CATALOG_MANAGER))
    )
    for window in CERTIFICATE_ALERT_DAYS:
        limit = today() + dt.timedelta(days=window)
        certificates = (
            session.scalars(
                select(Certificate).where(
                    Certificate.is_archived.is_(False),
                    Certificate.expiry_date.is_not(None),
                    Certificate.expiry_date <= limit,
                    Certificate.expiry_date >= today(),
                )
            )
            .unique()
            .all()
        )
        for certificate in certificates:
            rule = f"certificate.expiry_{window}"
            if _task_exists(session, rule, "certificate", certificate.id):
                continue
            create_task(
                session,
                title=f"Certificate '{certificate.name}' expires in {window} days",
                rule_code=rule,
                entity_type="certificate",
                entity_id=certificate.id,
                assignee_id=catalog_manager.id if catalog_manager else None,
                due_date=certificate.expiry_date,
                priority="critical" if window <= 7 else "high",
            )
            counters["certificate_expiry"] += 1

    session.flush()
    return counters


def list_tasks(
    session: Session,
    *,
    assignee_id: int | None = None,
    status: str | None = "open",
    overdue_only: bool = False,
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 500,
) -> list[dict]:
    """Filtered task list."""
    stmt = select(Task).where(Task.is_archived.is_(False))
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if status:
        stmt = stmt.where(Task.status == status)
    if overdue_only:
        stmt = stmt.where(Task.due_date.is_not(None), Task.due_date < today())
    if entity_type:
        stmt = stmt.where(Task.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(Task.entity_id == entity_id)
    rows = (
        session.scalars(
            stmt.order_by(Task.due_date.is_(None), Task.due_date, Task.id.desc()).limit(limit)
        )
        .unique()
        .all()
    )
    users = {
        row.id: (row.full_name or row.username)
        for row in session.scalars(select(User)).unique().all()
    }
    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "entity_type": task.entity_type or "",
            "entity_id": task.entity_id,
            "buyer_id": task.buyer_id,
            "lead_id": task.lead_id,
            "assignee_id": task.assignee_id,
            "assignee": users.get(task.assignee_id, ""),
            "due_date": task.due_date,
            "overdue": bool(task.due_date and task.due_date < today() and task.status == "open"),
            "priority": task.priority,
            "status": task.status,
            "rule_code": task.rule_code or "",
        }
        for task in rows
    ]


def complete_task(session: Session, actor: CurrentUser, task_id: int) -> Task:
    """Mark a task as done."""
    task = session.get(Task, task_id)
    if task is None:
        raise NotFoundError("Task not found")
    task.status = "done"
    task.completed_at = now()
    session.flush()
    return task


def save_task(session: Session, actor: CurrentUser, values: dict) -> Task:
    """Create or update a manual task."""
    task_id = values.get("id")
    if task_id:
        task = session.get(Task, task_id)
        if task is None:
            raise NotFoundError("Task not found")
    else:
        task = Task(title=values.get("title") or "")
        session.add(task)
    for key in (
        "title",
        "description",
        "entity_type",
        "entity_id",
        "buyer_id",
        "lead_id",
        "assignee_id",
        "due_date",
        "priority",
        "status",
    ):
        if key in values:
            setattr(task, key, values[key])
    session.flush()
    return task
