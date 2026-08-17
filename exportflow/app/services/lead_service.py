"""Export lead pipeline: filtering, stage transitions and follow-up rules."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Buyer, Contract, Lead, Product, User
from app.services import audit_service, checklist_service, task_service
from app.services.auth_service import CurrentUser
from app.utils.enums import PIPELINE_STAGES
from app.utils.errors import NotFoundError, ValidationError
from app.utils.formatting import now, today

#: Stages that immediately close the deal.
CLOSED_STATUSES = ("closed_won", "closed_lost", "spam")


def search_leads(
    session: Session,
    *,
    text: str = "",
    country: str | None = None,
    category_id: int | None = None,
    product_id: int | None = None,
    source: str | None = None,
    manager_id: int | None = None,
    status: str | None = None,
    temperature: str | None = None,
    follow_up_before: dt.date | None = None,
    overdue_only: bool = False,
    include_archived: bool = False,
    include_closed: bool = True,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Filtered lead list used by the leads page and the pipeline board."""
    stmt = select(Lead)
    if not include_archived:
        stmt = stmt.where(Lead.is_archived.is_(False))
    if not include_closed:
        stmt = stmt.where(Lead.status.not_in(CLOSED_STATUSES))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                Lead.title.ilike(pattern),
                Lead.notes.ilike(pattern),
                Lead.next_step.ilike(pattern),
                Lead.tags.ilike(pattern),
                Lead.destination.ilike(pattern),
            )
        )
    if country:
        stmt = stmt.where(Lead.country == country)
    if category_id:
        stmt = stmt.where(Lead.category_id == category_id)
    if product_id:
        stmt = stmt.where(Lead.product_id == product_id)
    if source:
        stmt = stmt.where(Lead.source == source)
    if manager_id:
        stmt = stmt.where(Lead.manager_id == manager_id)
    if status:
        stmt = stmt.where(Lead.status == status)
    if temperature:
        stmt = stmt.where(Lead.temperature == temperature)
    if follow_up_before:
        stmt = stmt.where(Lead.next_follow_up.is_not(None), Lead.next_follow_up <= follow_up_before)
    if overdue_only:
        stmt = stmt.where(Lead.next_follow_up.is_not(None), Lead.next_follow_up < today())
    stmt = stmt.order_by(Lead.next_follow_up.is_(None), Lead.next_follow_up, Lead.id.desc())
    if limit:
        stmt = stmt.limit(limit).offset(offset)

    leads = list(session.scalars(stmt).unique())
    if not leads:
        return []
    managers = {
        row.id: (row.full_name or row.username)
        for row in session.scalars(select(User)).unique().all()
    }
    products = {
        row.id: row.display_name("en") for row in session.scalars(select(Product)).unique().all()
    }
    return [
        {
            "id": lead.id,
            "title": lead.title,
            "buyer_id": lead.buyer_id,
            "buyer": lead.buyer.company_name if lead.buyer else "",
            "country": lead.country or (lead.buyer.country if lead.buyer else ""),
            "product_id": lead.product_id,
            "product": products.get(lead.product_id, ""),
            "source": lead.source,
            "source_detail": lead.source_detail or "",
            "status": lead.status,
            "temperature": lead.temperature,
            "expected_value": lead.expected_value,
            "currency": lead.currency,
            "probability": lead.probability,
            "next_step": lead.next_step or "",
            "next_follow_up": lead.next_follow_up,
            "overdue": bool(lead.next_follow_up and lead.next_follow_up < today()),
            "manager_id": lead.manager_id,
            "manager": managers.get(lead.manager_id, ""),
            "incoterm": lead.incoterm or "",
            "destination": lead.destination or "",
            "lost_reason": lead.lost_reason or "",
            "created_at": lead.created_at,
            "is_archived": lead.is_archived,
        }
        for lead in leads
    ]


def get_lead(session: Session, lead_id: int) -> Lead:
    """Fetch a lead or raise :class:`NotFoundError`."""
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError("Lead not found")
    return lead


def lead_dict(session: Session, lead_id: int) -> dict:
    """Lead payload for the detail panel."""
    lead = get_lead(session, lead_id)
    data = {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}
    data["buyer"] = lead.buyer.company_name if lead.buyer else ""
    return data


def save_lead(session: Session, actor: CurrentUser, values: dict) -> Lead:
    """Create or update a lead."""
    actor.require("lead.edit")
    title = (values.get("title") or "").strip()
    if not title:
        raise ValidationError("Lead title is required", key="error.lead_title_required")
    lead_id = values.get("id")
    if lead_id:
        lead = get_lead(session, lead_id)
        action = "update"
        previous_status = lead.status
    else:
        lead = Lead(title=title)
        session.add(lead)
        action = "create"
        previous_status = None

    editable = {c.name for c in Lead.__table__.columns} - {
        "id",
        "created_at",
        "updated_at",
        "created_by_id",
        "updated_by_id",
        "is_archived",
        "archived_at",
    }
    for key, value in values.items():
        if key in editable:
            setattr(lead, key, value)

    if lead.buyer_id and not lead.country:
        buyer = session.get(Buyer, lead.buyer_id)
        if buyer is not None:
            lead.country = buyer.country
    lead.updated_by_id = actor.id
    session.flush()

    audit_service.record(
        session,
        action=action,
        entity_type="lead",
        entity_id=lead.id,
        summary=f"Lead '{lead.title}' {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    if action == "create":
        audit_service.add_activity(
            session,
            entity_type="lead",
            entity_id=lead.id,
            kind="created",
            title="Lead created",
            body=f"Source: {lead.source}",
            user_id=actor.id,
        )
    elif previous_status and previous_status != lead.status:
        _after_status_change(session, actor, lead, previous_status)
    return lead


def change_status(
    session: Session,
    actor: CurrentUser,
    lead_id: int,
    new_status: str,
    *,
    lost_reason: str | None = None,
    lost_comment: str | None = None,
    contract_id: int | None = None,
) -> Lead:
    """Move a lead to a new pipeline stage, enforcing the closing rules.

    ``closed_lost`` requires a loss reason and ``closed_won`` requires a linked
    contract (or an already existing contract for the lead).
    """
    actor.require("lead.edit")
    lead = get_lead(session, lead_id)
    previous = lead.status
    if previous == new_status:
        return lead

    if new_status == "closed_lost":
        if not lost_reason:
            raise ValidationError("A loss reason is required", key="error.lost_reason_required")
        lead.lost_reason = lost_reason
        lead.lost_comment = lost_comment
        lead.closed_at = now()
        lead.probability = 0
    elif new_status == "closed_won":
        has_contract = contract_id is not None or session.scalar(
            select(Contract).where(Contract.lead_id == lead_id, Contract.is_archived.is_(False))
        )
        if not has_contract:
            raise ValidationError(
                "A signed contract or confirmed order is required to win a deal",
                key="error.contract_required",
            )
        lead.won_at = now()
        lead.closed_at = now()
        lead.probability = 100
        lead.lost_reason = None

    lead.status = new_status
    session.flush()
    _after_status_change(session, actor, lead, previous)
    return lead


def _after_status_change(session: Session, actor: CurrentUser, lead: Lead, previous: str) -> None:
    """Write the timeline entry and apply status-driven automation."""
    audit_service.record(
        session,
        action="status_change",
        entity_type="lead",
        entity_id=lead.id,
        summary=f"Lead '{lead.title}': {previous} -> {lead.status}",
        details={"from": previous, "to": lead.status},
        user_id=actor.id,
        username=actor.username,
    )
    audit_service.add_activity(
        session,
        entity_type="lead",
        entity_id=lead.id,
        kind="status",
        title=f"Stage: {previous} → {lead.status}",
        user_id=actor.id,
    )
    checklist_service.apply_templates_for_status(session, actor, lead)
    task_service.apply_stage_rules(session, lead)


def assign_leads(
    session: Session, actor: CurrentUser, lead_ids: list[int], manager_id: int | None
) -> int:
    """Bulk-assign leads to an export/sales manager."""
    actor.require("lead.assign")
    count = 0
    for lead_id in lead_ids:
        lead = session.get(Lead, lead_id)
        if lead is None:
            continue
        lead.manager_id = manager_id
        count += 1
    session.flush()
    if count:
        audit_service.record(
            session,
            action="assign",
            entity_type="lead",
            summary=f"{count} lead(s) assigned to manager #{manager_id}",
            user_id=actor.id,
            username=actor.username,
        )
    return count


def archive_lead(session: Session, actor: CurrentUser, lead_id: int, reason: str = "") -> None:
    """Soft delete a lead."""
    actor.require("lead.edit")
    lead = get_lead(session, lead_id)
    lead.is_archived = True
    lead.archive_reason = reason or None
    session.flush()
    audit_service.record(
        session,
        action="archive",
        entity_type="lead",
        entity_id=lead.id,
        summary=f"Lead '{lead.title}' archived",
        user_id=actor.id,
        username=actor.username,
    )


def pipeline_board(session: Session, **filters) -> dict[str, list[dict]]:
    """Group open leads by pipeline stage for the kanban workspace."""
    rows = search_leads(session, **filters)
    board: dict[str, list[dict]] = {stage: [] for stage in PIPELINE_STAGES}
    for row in rows:
        board.setdefault(row["status"], []).append(row)
    return board


def stage_totals(board: dict[str, list[dict]]) -> dict[str, dict]:
    """Per-stage deal count and expected value."""
    return {
        stage: {
            "count": len(items),
            "value": round(sum(item["expected_value"] or 0 for item in items), 2),
        }
        for stage, items in board.items()
    }
