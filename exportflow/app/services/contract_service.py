"""Export contracts and revenue recognition."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Buyer, Contract, Quotation, RevenueRecord, Shipment
from app.services import audit_service, quotation_service
from app.services.auth_service import CurrentUser
from app.utils.errors import NotFoundError, ValidationError
from app.utils.formatting import today


def list_contracts(
    session: Session,
    *,
    text: str = "",
    buyer_id: int | None = None,
    status: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Filtered contract register."""
    stmt = select(Contract)
    if not include_archived:
        stmt = stmt.where(Contract.is_archived.is_(False))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(or_(Contract.number.ilike(pattern), Contract.notes.ilike(pattern)))
    if buyer_id:
        stmt = stmt.where(Contract.buyer_id == buyer_id)
    if status:
        stmt = stmt.where(Contract.status == status)
    rows = (
        session.scalars(stmt.order_by(Contract.sign_date.desc(), Contract.id.desc())).unique().all()
    )
    buyers = {b.id: b.company_name for b in session.scalars(select(Buyer)).unique().all()}
    return [
        {
            "id": row.id,
            "number": row.number,
            "buyer_id": row.buyer_id,
            "buyer": buyers.get(row.buyer_id, ""),
            "lead_id": row.lead_id,
            "quotation_id": row.quotation_id,
            "sign_date": row.sign_date,
            "valid_until": row.valid_until,
            "currency": row.currency,
            "amount": row.amount,
            "incoterm": row.incoterm or "",
            "payment_terms": row.payment_terms or "",
            "status": row.status,
            "file_path": row.file_path or "",
            "notes": row.notes or "",
        }
        for row in rows
    ]


def save_contract(session: Session, actor: CurrentUser, values: dict) -> Contract:
    """Create or update an export contract."""
    actor.require("contract.edit")
    if not values.get("buyer_id"):
        raise ValidationError("Buyer is required", key="error.buyer_required")
    contract_id = values.get("id")
    if contract_id:
        contract = session.get(Contract, contract_id)
        if contract is None:
            raise NotFoundError("Contract not found")
        action = "update"
    else:
        contract = Contract(
            number=values.get("number")
            or quotation_service.next_number(session, "C", Contract, Contract.number),
            buyer_id=values["buyer_id"],
        )
        session.add(contract)
        action = "create"

    for key in (
        "buyer_id",
        "lead_id",
        "quotation_id",
        "sign_date",
        "valid_until",
        "currency",
        "amount",
        "incoterm",
        "payment_terms",
        "delivery_terms",
        "status",
        "file_path",
        "notes",
    ):
        if key in values:
            setattr(contract, key, values[key])
    session.flush()

    audit_service.record(
        session,
        action=action,
        entity_type="contract",
        entity_id=contract.id,
        summary=f"Contract {contract.number} {action}d ({contract.amount} {contract.currency})",
        user_id=actor.id,
        username=actor.username,
    )
    if contract.lead_id:
        audit_service.add_activity(
            session,
            entity_type="lead",
            entity_id=contract.lead_id,
            kind="contract",
            title=f"Contract {contract.number} {action}d",
            user_id=actor.id,
        )
    return contract


def create_from_quotation(session: Session, actor: CurrentUser, quotation_id: int) -> Contract:
    """Draft a contract using an accepted quotation as its basis."""
    actor.require("contract.edit")
    quotation = session.get(Quotation, quotation_id)
    if quotation is None:
        raise NotFoundError("Quotation not found")
    return save_contract(
        session,
        actor,
        {
            "buyer_id": quotation.buyer_id,
            "lead_id": quotation.lead_id,
            "quotation_id": quotation.id,
            "sign_date": today(),
            "currency": quotation.currency,
            "amount": quotation.grand_total,
            "incoterm": quotation.incoterm,
            "payment_terms": quotation.payment_terms,
            "delivery_terms": quotation.delivery_terms,
            "status": "draft",
        },
    )


def archive_contract(session: Session, actor: CurrentUser, contract_id: int) -> None:
    """Soft delete a contract."""
    actor.require("contract.edit")
    contract = session.get(Contract, contract_id)
    if contract is not None:
        contract.is_archived = True
        session.flush()


# ------------------------------------------------------------------- revenue
def record_revenue(session: Session, actor: CurrentUser, values: dict) -> RevenueRecord:
    """Register expected/actual revenue for a delivered shipment or contract."""
    actor.require("contract.edit")
    shipment_id = values.get("shipment_id")
    if shipment_id:
        shipment = session.get(Shipment, shipment_id)
        if shipment is None:
            raise NotFoundError("Shipment not found")
        if shipment.status != "delivered":
            raise ValidationError(
                "Actual revenue can only be recorded for a delivered shipment",
                key="error.shipment_not_delivered",
            )
    record = RevenueRecord(
        contract_id=values.get("contract_id"),
        lead_id=values.get("lead_id"),
        shipment_id=shipment_id,
        buyer_id=values.get("buyer_id"),
        record_date=values.get("record_date") or today(),
        currency=values.get("currency") or "USD",
        expected_amount=float(values.get("expected_amount") or 0),
        actual_amount=float(values.get("actual_amount") or 0),
        kind=values.get("kind") or "shipment",
        notes=values.get("notes"),
    )
    session.add(record)
    session.flush()
    audit_service.record(
        session,
        action="create",
        entity_type="revenue",
        entity_id=record.id,
        summary=f"Revenue {record.actual_amount} {record.currency} recorded",
        user_id=actor.id,
        username=actor.username,
    )
    return record


def list_revenue(session: Session, *, lead_id: int | None = None) -> list[dict]:
    """Revenue records, optionally scoped to a deal."""
    stmt = select(RevenueRecord).order_by(RevenueRecord.record_date.desc())
    if lead_id:
        stmt = stmt.where(RevenueRecord.lead_id == lead_id)
    return [
        {
            "id": row.id,
            "record_date": row.record_date,
            "buyer_id": row.buyer_id,
            "lead_id": row.lead_id,
            "contract_id": row.contract_id,
            "shipment_id": row.shipment_id,
            "currency": row.currency,
            "expected_amount": row.expected_amount,
            "actual_amount": row.actual_amount,
            "delta": round(row.actual_amount - row.expected_amount, 2),
            "kind": row.kind,
            "notes": row.notes or "",
        }
        for row in session.scalars(stmt).all()
    ]
