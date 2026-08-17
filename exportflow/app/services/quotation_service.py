"""RFQ intake and the quotation workflow (totals, approval, sending)."""

from __future__ import annotations

import datetime as dt
import json

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    RFQ,
    Buyer,
    Lead,
    Product,
    ProductPrice,
    Quotation,
    QuotationItem,
    QuotationVersion,
    RFQItem,
    User,
)
from app.services import audit_service, document_service, product_service, task_service
from app.services.auth_service import CurrentUser
from app.utils.enums import PORT_REQUIRED_INCOTERMS, QUOTATION_SENT_STATUSES
from app.utils.errors import NotFoundError, ValidationError, WorkflowError
from app.utils.formatting import now, today


# --------------------------------------------------------------- numbering
def next_number(session: Session, prefix: str, model, column) -> str:
    """Generate the next sequential document number (``Q-2026-0001``)."""
    year = today().year
    pattern = f"{prefix}-{year}-%"
    last = session.scalar(select(func.max(column)).where(column.like(pattern)))
    sequence = 1
    if last:
        try:
            sequence = int(str(last).rsplit("-", 1)[-1]) + 1
        except ValueError:
            sequence = 1
    return f"{prefix}-{year}-{sequence:04d}"


# --------------------------------------------------------------------- RFQ
def list_rfqs(
    session: Session,
    *,
    text: str = "",
    buyer_id: int | None = None,
    status: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Filtered RFQ register."""
    stmt = select(RFQ)
    if not include_archived:
        stmt = stmt.where(RFQ.is_archived.is_(False))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                RFQ.number.ilike(pattern),
                RFQ.destination.ilike(pattern),
                RFQ.internal_notes.ilike(pattern),
            )
        )
    if buyer_id:
        stmt = stmt.where(RFQ.buyer_id == buyer_id)
    if status:
        stmt = stmt.where(RFQ.status == status)
    rows = session.scalars(stmt.order_by(RFQ.received_at.desc(), RFQ.id.desc())).unique().all()
    buyers = {b.id: b.company_name for b in session.scalars(select(Buyer)).unique().all()}
    return [
        {
            "id": row.id,
            "number": row.number,
            "buyer_id": row.buyer_id,
            "buyer": buyers.get(row.buyer_id, ""),
            "lead_id": row.lead_id,
            "received_at": row.received_at,
            "deadline": row.deadline,
            "overdue": bool(row.deadline and row.deadline < today() and row.status == "new"),
            "target_incoterm": row.target_incoterm or "",
            "destination": row.destination or "",
            "currency": row.currency,
            "status": row.status,
            "items": len(row.items),
            "certificate_requirements": row.certificate_requirements or "",
            "payment_condition": row.payment_condition or "",
        }
        for row in rows
    ]


def rfq_dict(session: Session, rfq_id: int) -> dict:
    """Full RFQ payload including its item lines."""
    rfq = session.get(RFQ, rfq_id)
    if rfq is None:
        raise NotFoundError("RFQ not found")
    data = {column.name: getattr(rfq, column.name) for column in RFQ.__table__.columns}
    data["items"] = [
        {
            "id": item.id,
            "product_id": item.product_id,
            "description": item.description,
            "quantity": item.quantity,
            "unit": item.unit,
            "target_price": item.target_price,
            "notes": item.notes or "",
        }
        for item in rfq.items
    ]
    return data


def save_rfq(
    session: Session, actor: CurrentUser, values: dict, items: list[dict] | None = None
) -> RFQ:
    """Create or update an RFQ together with its requested lines."""
    actor.require("rfq.edit")
    if not values.get("buyer_id"):
        raise ValidationError("Buyer is required", key="error.buyer_required")
    rfq_id = values.get("id")
    if rfq_id:
        rfq = session.get(RFQ, rfq_id)
        if rfq is None:
            raise NotFoundError("RFQ not found")
        action = "update"
    else:
        rfq = RFQ(
            number=values.get("number") or next_number(session, "RFQ", RFQ, RFQ.number),
            buyer_id=values["buyer_id"],
            received_at=values.get("received_at") or today(),
        )
        session.add(rfq)
        action = "create"

    for key in (
        "buyer_id",
        "lead_id",
        "received_at",
        "deadline",
        "target_incoterm",
        "destination",
        "payment_condition",
        "certificate_requirements",
        "packaging_requirements",
        "currency",
        "status",
        "internal_notes",
    ):
        if key in values:
            setattr(rfq, key, values[key])
    session.flush()

    if items is not None:
        for item in list(rfq.items):
            session.delete(item)
        session.flush()
        for item in items:
            session.add(
                RFQItem(
                    rfq_id=rfq.id,
                    product_id=item.get("product_id"),
                    description=item.get("description") or "",
                    quantity=float(item.get("quantity") or 0),
                    unit=item.get("unit") or "pcs",
                    target_price=item.get("target_price"),
                    notes=item.get("notes"),
                )
            )
        session.flush()
        # The cached collection is stale after the delete/insert cycle.
        session.expire(rfq, ["items"])

    audit_service.record(
        session,
        action=action,
        entity_type="rfq",
        entity_id=rfq.id,
        summary=f"RFQ {rfq.number} {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    if rfq.lead_id:
        audit_service.add_activity(
            session,
            entity_type="lead",
            entity_id=rfq.lead_id,
            kind="rfq",
            title=f"RFQ {rfq.number} {action}d",
            user_id=actor.id,
        )
    return rfq


def archive_rfq(session: Session, actor: CurrentUser, rfq_id: int) -> None:
    """Soft delete an RFQ."""
    actor.require("rfq.edit")
    rfq = session.get(RFQ, rfq_id)
    if rfq is not None:
        rfq.is_archived = True
        session.flush()


# ---------------------------------------------------------------- quotation
def compute_totals(
    items: list[dict],
    freight: float = 0.0,
    insurance: float = 0.0,
    discount: float = 0.0,
) -> dict:
    """Compute line totals, subtotal and grand total.

    ``Line Total = Quantity x Unit Price``,
    ``Subtotal = sum(Line Total)``,
    ``Grand Total = Subtotal + Freight + Insurance - Discount``.
    """
    line_totals: list[float] = []
    for item in items:
        quantity = float(item.get("quantity") or 0)
        unit_price = float(item.get("unit_price") or 0)
        line_total = round(quantity * unit_price, 2)
        item["line_total"] = line_total
        line_totals.append(line_total)
    subtotal = round(sum(line_totals), 2)
    grand_total = round(
        subtotal + float(freight or 0) + float(insurance or 0) - float(discount or 0), 2
    )
    cost = round(
        sum(float(i.get("cost_price") or 0) * float(i.get("quantity") or 0) for i in items), 2
    )
    margin = round(subtotal - cost, 2)
    margin_percent = round(margin * 100.0 / subtotal, 2) if subtotal else 0.0
    return {
        "subtotal": subtotal,
        "grand_total": grand_total,
        "cost": cost,
        "margin": margin,
        "margin_percent": margin_percent,
    }


def list_quotations(
    session: Session,
    *,
    text: str = "",
    buyer_id: int | None = None,
    status: str | None = None,
    manager_id: int | None = None,
    incoterm: str | None = None,
    currency: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Filtered quotation register."""
    stmt = select(Quotation)
    if not include_archived:
        stmt = stmt.where(Quotation.is_archived.is_(False))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                Quotation.number.ilike(pattern),
                Quotation.destination.ilike(pattern),
                Quotation.remarks.ilike(pattern),
            )
        )
    if buyer_id:
        stmt = stmt.where(Quotation.buyer_id == buyer_id)
    if status:
        stmt = stmt.where(Quotation.status == status)
    if manager_id:
        stmt = stmt.where(Quotation.manager_id == manager_id)
    if incoterm:
        stmt = stmt.where(Quotation.incoterm == incoterm)
    if currency:
        stmt = stmt.where(Quotation.currency == currency)
    if date_from:
        stmt = stmt.where(Quotation.issue_date >= date_from)
    if date_to:
        stmt = stmt.where(Quotation.issue_date <= date_to)

    rows = (
        session.scalars(stmt.order_by(Quotation.issue_date.desc(), Quotation.id.desc()))
        .unique()
        .all()
    )
    buyers = {b.id: b for b in session.scalars(select(Buyer)).unique().all()}
    users = {
        u.id: (u.full_name or u.username) for u in session.scalars(select(User)).unique().all()
    }
    return [
        {
            "id": row.id,
            "number": row.number,
            "revision": row.revision,
            "buyer_id": row.buyer_id,
            "buyer": buyers[row.buyer_id].company_name if row.buyer_id in buyers else "",
            "country": buyers[row.buyer_id].country if row.buyer_id in buyers else "",
            "lead_id": row.lead_id,
            "currency": row.currency,
            "issue_date": row.issue_date,
            "valid_until": row.valid_until,
            "expired": bool(row.valid_until and row.valid_until < today()),
            "incoterm": row.incoterm,
            "loading_port": row.loading_port or "",
            "destination": row.destination or "",
            "subtotal": row.subtotal,
            "grand_total": row.grand_total,
            "status": row.status,
            "manager_id": row.manager_id,
            "manager": users.get(row.manager_id, ""),
            "items": len(row.items),
            "sent_at": row.sent_at,
            "is_archived": row.is_archived,
        }
        for row in rows
    ]


def quotation_dict(session: Session, quotation_id: int) -> dict:
    """Full quotation payload used by the editor and the PDF builder."""
    quotation = get_quotation(session, quotation_id)
    data = {c.name: getattr(quotation, c.name) for c in Quotation.__table__.columns}
    products = {p.id: p for p in session.scalars(select(Product)).unique().all()}
    data["items"] = [
        {
            "id": item.id,
            "product_id": item.product_id,
            "price_id": item.price_id,
            "sku": products[item.product_id].sku if item.product_id in products else "",
            "description": item.description,
            "hs_code": item.hs_code or "",
            "quantity": item.quantity,
            "unit": item.unit,
            "unit_price": item.unit_price,
            "cost_price": item.cost_price,
            "line_total": item.line_total,
            "moq": item.moq,
            "lead_time_days": item.lead_time_days,
            "packaging": item.packaging or "",
        }
        for item in sorted(quotation.items, key=lambda i: i.sort_order)
    ]
    buyer = session.get(Buyer, quotation.buyer_id)
    data["buyer"] = buyer.company_name if buyer else ""
    data["buyer_country"] = buyer.country if buyer else ""
    data["buyer_contact"] = buyer.contact_person if buyer else ""
    data["buyer_email"] = buyer.email if buyer else ""
    data["buyer_address"] = buyer.address if buyer else ""
    data["versions"] = [
        {
            "id": v.id,
            "revision": v.revision,
            "status": v.status,
            "grand_total": v.grand_total,
            "created_at": v.created_at,
            "comment": v.comment or "",
        }
        for v in sorted(quotation.versions, key=lambda v: v.revision, reverse=True)
    ]
    return data


def get_quotation(session: Session, quotation_id: int) -> Quotation:
    """Fetch a quotation or raise :class:`NotFoundError`."""
    quotation = session.get(Quotation, quotation_id)
    if quotation is None:
        raise NotFoundError("Quotation not found")
    return quotation


def suggest_line_from_price(
    session: Session, product_id: int, price_id: int, quantity: float
) -> dict:
    """Build a quotation line from an approved, still valid price."""
    price = session.get(ProductPrice, price_id)
    product = session.get(Product, product_id)
    if price is None or product is None:
        raise NotFoundError("Product or price not found")
    if not product_service.is_price_valid(price):
        raise ValidationError(
            "This price is not approved or has expired", key="error.price_not_usable"
        )
    return {
        "product_id": product.id,
        "price_id": price.id,
        "description": product.display_name("en"),
        "hs_code": product.hs_code,
        "quantity": quantity,
        "unit": product.unit,
        "unit_price": price.unit_price,
        "cost_price": 0.0,
        "moq": price.moq or product.moq,
        "lead_time_days": price.lead_time_days or product.lead_time_days,
        "packaging": product.packaging_type,
    }


def validate_quotation(session: Session, values: dict, items: list[dict]) -> list[str]:
    """Return non-blocking warnings for a quotation about to be saved/sent."""
    warnings: list[str] = []
    incoterm = values.get("incoterm") or ""
    if incoterm in PORT_REQUIRED_INCOTERMS and not (values.get("loading_port") or "").strip():
        warnings.append("warning.loading_port_missing")
    valid_until = values.get("valid_until")
    if valid_until and valid_until < today():
        warnings.append("warning.quotation_expired")
    for item in items:
        moq = item.get("moq")
        if moq and float(item.get("quantity") or 0) < float(moq):
            warnings.append("warning.below_moq")
            break
        price_id = item.get("price_id")
        if price_id:
            price = session.get(ProductPrice, price_id)
            if price is not None and not product_service.is_price_valid(price):
                warnings.append("warning.price_expired")
                break
    required_certificates = values.get("certificate_refs") or ""
    if required_certificates:
        product_ids = [item["product_id"] for item in items if item.get("product_id")]
        missing = document_service.missing_certificates(session, product_ids, required_certificates)
        if missing:
            warnings.append("warning.certificate_missing")
    return warnings


def save_quotation(
    session: Session,
    actor: CurrentUser,
    values: dict,
    items: list[dict],
) -> Quotation:
    """Create or update a quotation and recompute its totals.

    Prices that are not approved or already expired are rejected so that an
    outdated price can never reach a buyer.
    """
    actor.require("quotation.edit")
    if not values.get("buyer_id"):
        raise ValidationError("Buyer is required", key="error.buyer_required")
    if not items:
        raise ValidationError("At least one line item is required", key="error.items_required")

    for item in items:
        price_id = item.get("price_id")
        if price_id:
            price = session.get(ProductPrice, price_id)
            if price is not None and not product_service.is_price_valid(price):
                raise ValidationError(
                    "An expired or unapproved price cannot be used in a quotation",
                    key="error.price_not_usable",
                )

    quotation_id = values.get("id")
    if quotation_id:
        quotation = get_quotation(session, quotation_id)
        if quotation.status in ("accepted", "cancelled"):
            raise WorkflowError(
                "A finalised quotation cannot be edited", key="error.quotation_locked"
            )
        action = "update"
    else:
        quotation = Quotation(
            number=values.get("number") or next_number(session, "Q", Quotation, Quotation.number),
            buyer_id=values["buyer_id"],
            issue_date=values.get("issue_date") or today(),
        )
        session.add(quotation)
        action = "create"

    for key in (
        "buyer_id",
        "lead_id",
        "rfq_id",
        "language",
        "currency",
        "issue_date",
        "valid_until",
        "payment_terms",
        "delivery_terms",
        "incoterm",
        "loading_port",
        "destination",
        "lead_time_days",
        "packaging",
        "certificate_refs",
        "intro_text",
        "remarks",
        "freight_cost",
        "insurance_cost",
        "discount",
        "manager_id",
    ):
        if key in values:
            setattr(quotation, key, values[key])
    if quotation.manager_id is None:
        quotation.manager_id = actor.id
    session.flush()

    for item in list(quotation.items):
        session.delete(item)
    session.flush()

    totals = compute_totals(
        items, quotation.freight_cost, quotation.insurance_cost, quotation.discount
    )
    for order, item in enumerate(items):
        session.add(
            QuotationItem(
                quotation_id=quotation.id,
                product_id=item.get("product_id"),
                price_id=item.get("price_id"),
                description=item.get("description") or "",
                hs_code=item.get("hs_code"),
                quantity=float(item.get("quantity") or 0),
                unit=item.get("unit") or "pcs",
                unit_price=float(item.get("unit_price") or 0),
                cost_price=float(item.get("cost_price") or 0),
                line_total=float(item.get("line_total") or 0),
                moq=item.get("moq"),
                lead_time_days=item.get("lead_time_days"),
                packaging=item.get("packaging"),
                sort_order=order,
            )
        )
    session.flush()
    session.expire(quotation, ["items"])
    quotation.subtotal = totals["subtotal"]
    quotation.grand_total = totals["grand_total"]

    # Editing an approved/sent quotation drops it back for a new review.
    if action == "update" and quotation.status in ("approved",) + QUOTATION_SENT_STATUSES:
        quotation.status = "review_required"
        quotation.approved_at = None
        quotation.approved_by_id = None
    elif action == "create" and not quotation.status:
        quotation.status = "draft"
    session.flush()

    _snapshot(session, quotation, comment=f"{action} by {actor.username}")
    audit_service.record(
        session,
        action=action,
        entity_type="quotation",
        entity_id=quotation.id,
        summary=f"Quotation {quotation.number} {action}d ({quotation.grand_total} {quotation.currency})",
        user_id=actor.id,
        username=actor.username,
    )
    if quotation.lead_id:
        audit_service.add_activity(
            session,
            entity_type="lead",
            entity_id=quotation.lead_id,
            kind="quotation",
            title=f"Quotation {quotation.number} {action}d",
            user_id=actor.id,
        )
    return quotation


def _snapshot(session: Session, quotation: Quotation, comment: str = "") -> QuotationVersion:
    """Store an immutable JSON snapshot of the current quotation state."""
    payload = {
        "number": quotation.number,
        "status": quotation.status,
        "currency": quotation.currency,
        "incoterm": quotation.incoterm,
        "issue_date": str(quotation.issue_date),
        "valid_until": str(quotation.valid_until) if quotation.valid_until else None,
        "subtotal": quotation.subtotal,
        "grand_total": quotation.grand_total,
        "items": [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            }
            for item in quotation.items
        ],
    }
    version = QuotationVersion(
        quotation_id=quotation.id,
        revision=quotation.revision,
        status=quotation.status,
        grand_total=quotation.grand_total,
        payload=json.dumps(payload, ensure_ascii=False),
        comment=comment[:300] if comment else None,
    )
    session.add(version)
    session.flush()
    return version


def submit_for_review(session: Session, actor: CurrentUser, quotation_id: int) -> Quotation:
    """Move a draft quotation into the approval queue."""
    actor.require("quotation.edit")
    quotation = get_quotation(session, quotation_id)
    if quotation.status not in ("draft", "review_required"):
        raise WorkflowError("Only drafts can be submitted", key="error.quotation_not_draft")
    quotation.status = "review_required"
    session.flush()
    audit_service.record(
        session,
        action="status_change",
        entity_type="quotation",
        entity_id=quotation.id,
        summary=f"Quotation {quotation.number} submitted for review",
        user_id=actor.id,
        username=actor.username,
    )
    return quotation


def approve_quotation(session: Session, actor: CurrentUser, quotation_id: int) -> Quotation:
    """Approve a quotation (requires ``quotation.approve``)."""
    actor.require("quotation.approve")
    quotation = get_quotation(session, quotation_id)
    if quotation.status not in ("draft", "review_required"):
        raise WorkflowError(
            "Only a draft or a quotation under review can be approved",
            key="error.quotation_not_reviewable",
        )
    if quotation.valid_until and quotation.valid_until < today():
        raise ValidationError(
            "The quotation validity date has passed", key="error.quotation_expired"
        )
    quotation.status = "approved"
    quotation.approved_by_id = actor.id
    quotation.approved_at = now()
    session.flush()
    _snapshot(session, quotation, comment=f"approved by {actor.username}")
    audit_service.record(
        session,
        action="approve",
        entity_type="quotation",
        entity_id=quotation.id,
        summary=f"Quotation {quotation.number} approved",
        user_id=actor.id,
        username=actor.username,
    )
    return quotation


def mark_sent(
    session: Session, actor: CurrentUser, quotation_id: int, force: bool = False
) -> Quotation:
    """Mark an approved quotation as sent to the buyer.

    A quotation that has not been approved can never be sent.
    """
    actor.require("quotation.send")
    quotation = get_quotation(session, quotation_id)
    if quotation.status != "approved" and not (
        force and quotation.status in QUOTATION_SENT_STATUSES
    ):
        raise WorkflowError(
            "The quotation must be approved before it is sent",
            key="error.quotation_not_approved",
        )
    quotation.status = "sent"
    quotation.sent_at = now()
    quotation.revision = quotation.revision
    session.flush()
    audit_service.record(
        session,
        action="send",
        entity_type="quotation",
        entity_id=quotation.id,
        summary=f"Quotation {quotation.number} marked as sent",
        user_id=actor.id,
        username=actor.username,
    )
    if quotation.lead_id:
        from app.services import lead_service

        lead = session.get(Lead, quotation.lead_id)
        if lead is not None and lead.status in ("new", "in_review", "qualified", "rfq_received"):
            lead_service.change_status(session, actor, lead.id, "quotation_sent")
    task_service.create_task(
        session,
        title=f"Follow up quotation {quotation.number}",
        rule_code="quotation.followup",
        entity_type="quotation",
        entity_id=quotation.id,
        buyer_id=quotation.buyer_id,
        lead_id=quotation.lead_id,
        assignee_id=quotation.manager_id,
        due_date=today() + dt.timedelta(days=task_service.FOLLOW_UP_AFTER_QUOTATION_DAYS),
        priority="high",
    )
    return quotation


def set_status(session: Session, actor: CurrentUser, quotation_id: int, status: str) -> Quotation:
    """Manually set an engagement status (viewed / replied / accepted / ...)."""
    actor.require("quotation.edit")
    quotation = get_quotation(session, quotation_id)
    previous = quotation.status
    quotation.status = status
    if status == "viewed" and not quotation.viewed_at:
        quotation.viewed_at = now()
    if status == "buyer_replied":
        quotation.replied_at = now()
    session.flush()
    audit_service.record(
        session,
        action="status_change",
        entity_type="quotation",
        entity_id=quotation.id,
        summary=f"Quotation {quotation.number}: {previous} -> {status}",
        user_id=actor.id,
        username=actor.username,
    )
    return quotation


def duplicate_quotation(session: Session, actor: CurrentUser, quotation_id: int) -> Quotation:
    """Create an editable copy of an existing quotation."""
    actor.require("quotation.edit")
    source = get_quotation(session, quotation_id)
    clone = Quotation(
        number=next_number(session, "Q", Quotation, Quotation.number),
        revision=1,
        buyer_id=source.buyer_id,
        lead_id=source.lead_id,
        rfq_id=source.rfq_id,
        language=source.language,
        currency=source.currency,
        issue_date=today(),
        valid_until=source.valid_until,
        payment_terms=source.payment_terms,
        delivery_terms=source.delivery_terms,
        incoterm=source.incoterm,
        loading_port=source.loading_port,
        destination=source.destination,
        lead_time_days=source.lead_time_days,
        packaging=source.packaging,
        certificate_refs=source.certificate_refs,
        intro_text=source.intro_text,
        remarks=source.remarks,
        freight_cost=source.freight_cost,
        insurance_cost=source.insurance_cost,
        discount=source.discount,
        subtotal=source.subtotal,
        grand_total=source.grand_total,
        status="draft",
        manager_id=actor.id,
    )
    session.add(clone)
    session.flush()
    for item in source.items:
        session.add(
            QuotationItem(
                quotation_id=clone.id,
                product_id=item.product_id,
                price_id=item.price_id,
                description=item.description,
                hs_code=item.hs_code,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                cost_price=item.cost_price,
                line_total=item.line_total,
                moq=item.moq,
                lead_time_days=item.lead_time_days,
                packaging=item.packaging,
                sort_order=item.sort_order,
            )
        )
    session.flush()
    audit_service.record(
        session,
        action="create",
        entity_type="quotation",
        entity_id=clone.id,
        summary=f"Quotation {clone.number} duplicated from {source.number}",
        user_id=actor.id,
        username=actor.username,
    )
    return clone


def new_revision(session: Session, actor: CurrentUser, quotation_id: int) -> Quotation:
    """Increment the revision number and reopen the quotation for editing."""
    actor.require("quotation.edit")
    quotation = get_quotation(session, quotation_id)
    _snapshot(session, quotation, comment="revision closed")
    quotation.revision += 1
    quotation.status = "draft"
    quotation.approved_at = None
    quotation.approved_by_id = None
    session.flush()
    return quotation


def archive_quotation(session: Session, actor: CurrentUser, quotation_id: int) -> None:
    """Soft delete a quotation."""
    actor.require("quotation.edit")
    quotation = get_quotation(session, quotation_id)
    quotation.is_archived = True
    session.flush()
    audit_service.record(
        session,
        action="archive",
        entity_type="quotation",
        entity_id=quotation.id,
        summary=f"Quotation {quotation.number} archived",
        user_id=actor.id,
        username=actor.username,
    )


def refresh_expired_quotations(session: Session) -> int:
    """Flag quotations whose validity date has passed."""
    rows = (
        session.scalars(
            select(Quotation).where(
                Quotation.is_archived.is_(False),
                Quotation.valid_until.is_not(None),
                Quotation.valid_until < today(),
                Quotation.status.in_(("sent", "viewed", "approved", "under_negotiation")),
            )
        )
        .unique()
        .all()
    )
    for row in rows:
        row.status = "expired"
    session.flush()
    return len(rows)
