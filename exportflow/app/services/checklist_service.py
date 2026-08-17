"""Export readiness checklists and their templates."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Checklist,
    ChecklistItem,
    ChecklistTemplate,
    ChecklistTemplateItem,
    Lead,
    User,
)
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.errors import NotFoundError, ValidationError
from app.utils.formatting import now, today


# ------------------------------------------------------------------ templates
def list_templates(session: Session, scope: str | None = None) -> list[dict]:
    """Return checklist templates with their item counts."""
    stmt = select(ChecklistTemplate).where(ChecklistTemplate.is_archived.is_(False))
    if scope:
        stmt = stmt.where(ChecklistTemplate.scope == scope)
    rows = session.scalars(stmt.order_by(ChecklistTemplate.name)).unique().all()
    return [
        {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "scope": row.scope,
            "trigger_status": row.trigger_status or "",
            "description": row.description or "",
            "item_count": len(row.items),
            "items": [
                {
                    "id": item.id,
                    "category": item.category,
                    "title": item.title,
                    "description": item.description or "",
                    "priority": item.priority,
                    "due_offset_days": item.due_offset_days,
                }
                for item in row.items
            ],
        }
        for row in rows
    ]


def save_template(session: Session, actor: CurrentUser, values: dict) -> ChecklistTemplate:
    """Create or update a checklist template together with its items."""
    actor.require("checklist.edit")
    template_id = values.get("id")
    if template_id:
        template = session.get(ChecklistTemplate, template_id)
        if template is None:
            raise NotFoundError("Checklist template not found")
    else:
        code = (values.get("code") or "").strip()
        if not code:
            raise ValidationError("Template code is required", key="error.code_required")
        template = ChecklistTemplate(code=code, name=values.get("name") or code)
        session.add(template)

    for key in ("code", "name", "scope", "trigger_status", "description"):
        if key in values:
            setattr(template, key, values[key])
    session.flush()

    if "items" in values:
        for item in list(template.items):
            session.delete(item)
        session.flush()
        for order, item in enumerate(values["items"]):
            session.add(
                ChecklistTemplateItem(
                    template_id=template.id,
                    category=item.get("category") or "product_readiness",
                    title=item.get("title") or "",
                    description=item.get("description"),
                    priority=item.get("priority") or "normal",
                    due_offset_days=int(item.get("due_offset_days") or 7),
                    sort_order=order,
                )
            )
        session.flush()

    audit_service.record(
        session,
        action="update" if template_id else "create",
        entity_type="checklist_template",
        entity_id=template.id,
        summary=f"Checklist template {template.name}",
        user_id=actor.id,
        username=actor.username,
    )
    return template


# ----------------------------------------------------------------- checklists
def apply_template(
    session: Session,
    actor: CurrentUser,
    template_id: int,
    scope: str,
    entity_id: int,
    *,
    base_date: dt.date | None = None,
    assignee_id: int | None = None,
) -> Checklist:
    """Instantiate a template for a concrete product/buyer/lead/shipment."""
    template = session.get(ChecklistTemplate, template_id)
    if template is None:
        raise NotFoundError("Checklist template not found")
    base_date = base_date or today()

    checklist = Checklist(
        name=template.name,
        scope=scope,
        entity_id=entity_id,
        template_id=template.id,
        status="open",
    )
    session.add(checklist)
    session.flush()

    for item in template.items:
        session.add(
            ChecklistItem(
                checklist_id=checklist.id,
                category=item.category,
                title=item.title,
                description=item.description,
                priority=item.priority,
                due_date=base_date + dt.timedelta(days=item.due_offset_days),
                assignee_id=assignee_id,
            )
        )
    session.flush()

    audit_service.record(
        session,
        action="create",
        entity_type="checklist",
        entity_id=checklist.id,
        summary=f"Checklist '{checklist.name}' applied to {scope} #{entity_id}",
        user_id=actor.id,
        username=actor.username,
    )
    return checklist


def apply_templates_for_status(session: Session, actor: CurrentUser, lead: Lead) -> list[Checklist]:
    """Auto-apply every template whose trigger matches the lead's new status.

    Templates already applied to the lead are skipped so that moving a deal back
    and forth does not create duplicates.
    """
    templates = (
        session.scalars(
            select(ChecklistTemplate).where(
                ChecklistTemplate.is_archived.is_(False),
                ChecklistTemplate.scope == "lead",
                ChecklistTemplate.trigger_status == lead.status,
            )
        )
        .unique()
        .all()
    )
    if not templates:
        return []

    existing = {
        row.template_id
        for row in session.scalars(
            select(Checklist).where(Checklist.scope == "lead", Checklist.entity_id == lead.id)
        ).all()
    }
    created: list[Checklist] = []
    for template in templates:
        if template.id in existing:
            continue
        created.append(
            apply_template(
                session,
                actor,
                template.id,
                "lead",
                lead.id,
                assignee_id=lead.manager_id,
            )
        )
    return created


def list_checklists(
    session: Session,
    *,
    scope: str | None = None,
    entity_id: int | None = None,
    category: str | None = None,
    only_overdue: bool = False,
) -> list[dict]:
    """Checklists with completion percentage and overdue counters."""
    stmt = select(Checklist).where(Checklist.is_archived.is_(False))
    if scope:
        stmt = stmt.where(Checklist.scope == scope)
    if entity_id is not None:
        stmt = stmt.where(Checklist.entity_id == entity_id)
    rows = session.scalars(stmt.order_by(Checklist.id.desc())).unique().all()

    result: list[dict] = []
    for checklist in rows:
        items = checklist.items
        if category:
            items = [item for item in items if item.category == category]
            if not items:
                continue
        overdue = [
            item for item in items if not item.is_done and item.due_date and item.due_date < today()
        ]
        if only_overdue and not overdue:
            continue
        done = sum(1 for item in items if item.is_done)
        result.append(
            {
                "id": checklist.id,
                "name": checklist.name,
                "scope": checklist.scope,
                "entity_id": checklist.entity_id,
                "status": checklist.status,
                "total": len(items),
                "done": done,
                "overdue": len(overdue),
                "completion": round(done * 100.0 / len(items), 1) if items else 0.0,
                "created_at": checklist.created_at,
            }
        )
    return result


def checklist_items(session: Session, checklist_id: int, category: str | None = None) -> list[dict]:
    """Items of one checklist, optionally filtered by category."""
    checklist = session.get(Checklist, checklist_id)
    if checklist is None:
        raise NotFoundError("Checklist not found")
    users = {
        row.id: (row.full_name or row.username)
        for row in session.scalars(select(User)).unique().all()
    }
    return [
        {
            "id": item.id,
            "category": item.category,
            "title": item.title,
            "description": item.description or "",
            "is_done": item.is_done,
            "done_at": item.done_at,
            "assignee_id": item.assignee_id,
            "assignee": users.get(item.assignee_id, ""),
            "due_date": item.due_date,
            "overdue": bool(not item.is_done and item.due_date and item.due_date < today()),
            "priority": item.priority,
            "file_path": item.file_path or "",
            "notes": item.notes or "",
        }
        for item in checklist.items
        if category is None or item.category == category
    ]


def create_checklist(
    session: Session, actor: CurrentUser, name: str, scope: str, entity_id: int
) -> Checklist:
    """Create an empty checklist."""
    actor.require("checklist.edit")
    checklist = Checklist(name=name, scope=scope, entity_id=entity_id)
    session.add(checklist)
    session.flush()
    return checklist


def save_item(session: Session, actor: CurrentUser, values: dict) -> ChecklistItem:
    """Create or update one checklist item."""
    actor.require("checklist.edit")
    item_id = values.get("id")
    if item_id:
        item = session.get(ChecklistItem, item_id)
        if item is None:
            raise NotFoundError("Checklist item not found")
    else:
        item = ChecklistItem(checklist_id=values["checklist_id"], title=values.get("title") or "")
        session.add(item)
    for key in (
        "category",
        "title",
        "description",
        "assignee_id",
        "due_date",
        "priority",
        "file_path",
        "notes",
    ):
        if key in values:
            setattr(item, key, values[key])
    session.flush()
    return item


def toggle_item(session: Session, actor: CurrentUser, item_id: int, done: bool) -> ChecklistItem:
    """Mark a checklist item as done or reopen it."""
    actor.require("checklist.edit")
    item = session.get(ChecklistItem, item_id)
    if item is None:
        raise NotFoundError("Checklist item not found")
    item.is_done = done
    item.done_at = now() if done else None
    session.flush()

    checklist = item.checklist
    if all(child.is_done for child in checklist.items):
        checklist.status = "completed"
    else:
        checklist.status = "open"
    session.flush()

    audit_service.record(
        session,
        action="update",
        entity_type="checklist_item",
        entity_id=item.id,
        summary=f"Checklist item '{item.title}' marked {'done' if done else 'open'}",
        user_id=actor.id,
        username=actor.username,
    )
    return item


def delete_item(session: Session, actor: CurrentUser, item_id: int) -> None:
    """Remove a checklist item."""
    actor.require("checklist.edit")
    item = session.get(ChecklistItem, item_id)
    if item is not None:
        session.delete(item)
        session.flush()


def overdue_summary(session: Session) -> list[dict]:
    """Every overdue checklist item across the whole database."""
    rows = session.scalars(
        select(ChecklistItem).where(
            ChecklistItem.is_done.is_(False),
            ChecklistItem.due_date.is_not(None),
            ChecklistItem.due_date < today(),
        )
    ).all()
    return [
        {
            "id": item.id,
            "checklist": item.checklist.name,
            "scope": item.checklist.scope,
            "entity_id": item.checklist.entity_id,
            "category": item.category,
            "title": item.title,
            "due_date": item.due_date,
            "days_overdue": (today() - item.due_date).days,
            "priority": item.priority,
        }
        for item in rows
        if item.checklist is not None and not item.checklist.is_archived
    ]
