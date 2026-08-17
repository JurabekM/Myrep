"""Buyer CRM: search, duplicate detection and contact management."""

from __future__ import annotations

import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Buyer, BuyerContact, Lead, Quotation, User
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.errors import NotFoundError, ValidationError

_NON_DIGITS = re.compile(r"\D+")


def normalize_phone(phone: str | None) -> str:
    """Reduce a phone number to digits so formatting differences do not matter."""
    if not phone:
        return ""
    digits = _NON_DIGITS.sub("", phone)
    return digits[-9:] if len(digits) > 9 else digits


def normalize_email(email: str | None) -> str:
    """Lowercase and trim an email address."""
    return (email or "").strip().lower()


def find_duplicates(
    session: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
    company_name: str | None = None,
    exclude_id: int | None = None,
) -> list[dict]:
    """Return existing buyers that look like the same company.

    Matching is done on normalised email, normalised phone tail and a
    case-insensitive company name comparison.
    """
    email_n = normalize_email(email)
    phone_n = normalize_phone(phone)
    name_n = (company_name or "").strip().lower()
    if not (email_n or phone_n or name_n):
        return []

    candidates = (
        session.scalars(
            select(Buyer).where(Buyer.is_archived.is_(False), Buyer.id != (exclude_id or 0))
        )
        .unique()
        .all()
    )

    matches: list[dict] = []
    for buyer in candidates:
        reasons: list[str] = []
        if email_n and normalize_email(buyer.email) == email_n:
            reasons.append("email")
        if phone_n and normalize_phone(buyer.phone) and normalize_phone(buyer.phone) == phone_n:
            reasons.append("phone")
        if name_n and buyer.company_name.strip().lower() == name_n:
            reasons.append("company_name")
        if reasons:
            matches.append(
                {
                    "id": buyer.id,
                    "company_name": buyer.company_name,
                    "country": buyer.country,
                    "email": buyer.email,
                    "phone": buyer.phone,
                    "reasons": reasons,
                }
            )
    return matches


def search_buyers(
    session: Session,
    *,
    text: str = "",
    country: str | None = None,
    buyer_type: str | None = None,
    source: str | None = None,
    manager_id: int | None = None,
    status: str | None = None,
    risk_level: str | None = None,
    include_archived: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Filtered buyer list for the buyers page."""
    stmt = select(Buyer)
    if not include_archived:
        stmt = stmt.where(Buyer.is_archived.is_(False))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                Buyer.company_name.ilike(pattern),
                Buyer.contact_person.ilike(pattern),
                Buyer.email.ilike(pattern),
                Buyer.phone.ilike(pattern),
                Buyer.city.ilike(pattern),
                Buyer.tags.ilike(pattern),
            )
        )
    if country:
        stmt = stmt.where(Buyer.country == country)
    if buyer_type:
        stmt = stmt.where(Buyer.buyer_type == buyer_type)
    if source:
        stmt = stmt.where(Buyer.source == source)
    if manager_id:
        stmt = stmt.where(Buyer.manager_id == manager_id)
    if status:
        stmt = stmt.where(Buyer.status == status)
    if risk_level:
        stmt = stmt.where(Buyer.risk_level == risk_level)
    stmt = stmt.order_by(Buyer.company_name)
    if limit:
        stmt = stmt.limit(limit).offset(offset)

    buyers = list(session.scalars(stmt).unique())
    if not buyers:
        return []
    ids = [b.id for b in buyers]
    lead_counts = dict(
        session.execute(
            select(Lead.buyer_id, func.count(Lead.id))
            .where(Lead.buyer_id.in_(ids), Lead.is_archived.is_(False))
            .group_by(Lead.buyer_id)
        ).all()
    )
    quote_counts = dict(
        session.execute(
            select(Quotation.buyer_id, func.count(Quotation.id))
            .where(Quotation.buyer_id.in_(ids), Quotation.is_archived.is_(False))
            .group_by(Quotation.buyer_id)
        ).all()
    )
    managers = {
        row.id: (row.full_name or row.username)
        for row in session.scalars(select(User)).unique().all()
    }
    return [
        {
            "id": b.id,
            "company_name": b.company_name,
            "contact_person": b.contact_person or "",
            "country": b.country,
            "city": b.city or "",
            "email": b.email or "",
            "phone": b.phone or "",
            "buyer_type": b.buyer_type,
            "source": b.source,
            "risk_level": b.risk_level,
            "status": b.status,
            "annual_potential": b.annual_potential,
            "manager_id": b.manager_id,
            "manager": managers.get(b.manager_id, ""),
            "leads": int(lead_counts.get(b.id, 0)),
            "quotations": int(quote_counts.get(b.id, 0)),
            "tags": b.tags or "",
            "is_archived": b.is_archived,
        }
        for b in buyers
    ]


def get_buyer(session: Session, buyer_id: int) -> Buyer:
    """Fetch a buyer or raise :class:`NotFoundError`."""
    buyer = session.get(Buyer, buyer_id)
    if buyer is None:
        raise NotFoundError("Buyer not found")
    return buyer


def buyer_dict(session: Session, buyer_id: int) -> dict:
    """Buyer payload with contacts for the detail panel."""
    buyer = get_buyer(session, buyer_id)
    data = {column.name: getattr(buyer, column.name) for column in Buyer.__table__.columns}
    data["contacts"] = [
        {
            "id": c.id,
            "full_name": c.full_name,
            "position": c.position or "",
            "email": c.email or "",
            "phone": c.phone or "",
            "messenger": c.messenger or "",
            "language": c.language,
            "is_primary": c.is_primary,
            "notes": c.notes or "",
        }
        for c in buyer.contacts
        if not c.is_archived
    ]
    return data


def save_buyer(
    session: Session, actor: CurrentUser, values: dict, allow_duplicate: bool = False
) -> Buyer:
    """Create or update a buyer, blocking obvious duplicates by default."""
    actor.require("buyer.edit")
    company_name = (values.get("company_name") or "").strip()
    if not company_name:
        raise ValidationError("Company name is required", key="error.company_name_required")
    buyer_id = values.get("id")

    if not allow_duplicate:
        duplicates = find_duplicates(
            session,
            email=values.get("email"),
            phone=values.get("phone"),
            company_name=company_name,
            exclude_id=buyer_id,
        )
        if duplicates:
            raise ValidationError(
                "A buyer with the same email/phone/name already exists",
                key="error.buyer_duplicate",
                matches=duplicates,
            )

    if buyer_id:
        buyer = get_buyer(session, buyer_id)
        action = "update"
    else:
        buyer = Buyer(company_name=company_name, country=values.get("country") or "")
        session.add(buyer)
        action = "create"

    editable = {c.name for c in Buyer.__table__.columns} - {
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
            setattr(buyer, key, value)
    buyer.updated_by_id = actor.id
    session.flush()

    audit_service.record(
        session,
        action=action,
        entity_type="buyer",
        entity_id=buyer.id,
        summary=f"Buyer {buyer.company_name} {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    audit_service.add_activity(
        session,
        entity_type="buyer",
        entity_id=buyer.id,
        kind=action,
        title=f"Buyer {action}d",
        user_id=actor.id,
    )
    return buyer


def archive_buyer(session: Session, actor: CurrentUser, buyer_id: int, reason: str = "") -> None:
    """Soft delete a buyer."""
    actor.require("buyer.edit")
    buyer = get_buyer(session, buyer_id)
    buyer.is_archived = True
    buyer.status = "archived"
    buyer.archive_reason = reason or None
    session.flush()
    audit_service.record(
        session,
        action="archive",
        entity_type="buyer",
        entity_id=buyer.id,
        summary=f"Buyer {buyer.company_name} archived",
        user_id=actor.id,
        username=actor.username,
    )


def save_contact(session: Session, actor: CurrentUser, values: dict) -> BuyerContact:
    """Create or update a contact person of a buyer."""
    actor.require("buyer.edit")
    contact_id = values.get("id")
    if contact_id:
        contact = session.get(BuyerContact, contact_id)
        if contact is None:
            raise NotFoundError("Contact not found")
    else:
        contact = BuyerContact(buyer_id=values["buyer_id"], full_name=values.get("full_name") or "")
        session.add(contact)
    for key in (
        "buyer_id",
        "full_name",
        "position",
        "email",
        "phone",
        "messenger",
        "language",
        "is_primary",
        "notes",
    ):
        if key in values:
            setattr(contact, key, values[key])
    if not contact.full_name:
        raise ValidationError("Contact name is required", key="error.contact_name_required")
    session.flush()
    if contact.is_primary:
        for sibling in contact.buyer.contacts:
            if sibling.id != contact.id:
                sibling.is_primary = False
        session.flush()
    return contact


def delete_contact(session: Session, actor: CurrentUser, contact_id: int) -> None:
    """Archive a contact person."""
    actor.require("buyer.edit")
    contact = session.get(BuyerContact, contact_id)
    if contact is not None:
        contact.is_archived = True
        session.flush()


def distinct_countries(session: Session) -> list[str]:
    """Sorted list of countries currently present in the buyer base."""
    rows = session.scalars(
        select(Buyer.country).where(Buyer.is_archived.is_(False)).distinct()
    ).all()
    return sorted({row for row in rows if row})
