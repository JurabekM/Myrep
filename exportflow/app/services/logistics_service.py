"""Shipments, freight quotes and shipping document data."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Buyer, FreightQuote, Product, Shipment, ShipmentItem
from app.services import audit_service, quotation_service
from app.services.auth_service import CurrentUser
from app.utils.enums import SHIPMENT_TRANSITIONS
from app.utils.errors import NotFoundError, ValidationError, WorkflowError
from app.utils.formatting import today


def list_shipments(
    session: Session,
    *,
    text: str = "",
    buyer_id: int | None = None,
    status: str | None = None,
    incoterm: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Filtered shipment register with delay detection."""
    stmt = select(Shipment)
    if not include_archived:
        stmt = stmt.where(Shipment.is_archived.is_(False))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                Shipment.number.ilike(pattern),
                Shipment.destination.ilike(pattern),
                Shipment.tracking_reference.ilike(pattern),
                Shipment.forwarder.ilike(pattern),
            )
        )
    if buyer_id:
        stmt = stmt.where(Shipment.buyer_id == buyer_id)
    if status:
        stmt = stmt.where(Shipment.status == status)
    if incoterm:
        stmt = stmt.where(Shipment.incoterm == incoterm)

    rows = (
        session.scalars(
            stmt.order_by(Shipment.etd.is_(None), Shipment.etd.desc(), Shipment.id.desc())
        )
        .unique()
        .all()
    )
    buyers = {b.id: b.company_name for b in session.scalars(select(Buyer)).unique().all()}
    result = []
    for row in rows:
        delayed = bool(
            row.eta
            and row.eta < today()
            and row.status not in ("delivered", "arrived", "cancelled")
        )
        result.append(
            {
                "id": row.id,
                "number": row.number,
                "buyer_id": row.buyer_id,
                "buyer": buyers.get(row.buyer_id, ""),
                "lead_id": row.lead_id,
                "incoterm": row.incoterm,
                "origin": row.origin or "",
                "loading_port": row.loading_port or "",
                "destination": row.destination or "",
                "container_type": row.container_type or "",
                "etd": row.etd,
                "eta": row.eta,
                "actual_departure": row.actual_departure,
                "actual_arrival": row.actual_arrival,
                "status": row.status,
                "customs_status": row.customs_status,
                "delayed": delayed,
                "gross_weight": row.gross_weight,
                "package_count": row.package_count,
                "currency": row.currency,
                "planned_cost": row.planned_cost,
                "actual_cost": row.total_cost,
                "cost_delta": round(row.total_cost - row.planned_cost, 2),
                "tracking_reference": row.tracking_reference or "",
                "items": len(row.items),
            }
        )
    return result


def get_shipment(session: Session, shipment_id: int) -> Shipment:
    """Fetch a shipment or raise :class:`NotFoundError`."""
    shipment = session.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found")
    return shipment


def shipment_dict(session: Session, shipment_id: int) -> dict:
    """Full shipment payload with item lines and freight quotes."""
    shipment = get_shipment(session, shipment_id)
    data = {c.name: getattr(shipment, c.name) for c in Shipment.__table__.columns}
    products = {p.id: p for p in session.scalars(select(Product)).unique().all()}
    data["items"] = [
        {
            "id": item.id,
            "product_id": item.product_id,
            "sku": products[item.product_id].sku if item.product_id in products else "",
            "description": item.description,
            "hs_code": item.hs_code or "",
            "quantity": item.quantity,
            "unit": item.unit,
            "unit_price": item.unit_price,
            "amount": item.amount,
            "packages": item.packages,
            "net_weight": item.net_weight,
            "gross_weight": item.gross_weight,
        }
        for item in sorted(shipment.items, key=lambda i: i.sort_order)
    ]
    data["freight_quotes"] = [
        {
            "id": quote.id,
            "forwarder": quote.forwarder,
            "mode": quote.mode,
            "currency": quote.currency,
            "price": quote.price,
            "transit_days": quote.transit_days,
            "valid_until": quote.valid_until,
            "is_selected": bool(quote.is_selected),
            "notes": quote.notes or "",
        }
        for quote in shipment.freight_quotes
    ]
    buyer = session.get(Buyer, shipment.buyer_id)
    data["buyer"] = buyer.company_name if buyer else ""
    data["buyer_address"] = buyer.address if buyer else ""
    data["buyer_country"] = buyer.country if buyer else ""
    data["planned_cost"] = shipment.planned_cost
    data["actual_cost"] = shipment.total_cost
    return data


def save_shipment(
    session: Session, actor: CurrentUser, values: dict, items: list[dict] | None = None
) -> Shipment:
    """Create or update a shipment and roll up its weights and package count."""
    actor.require("shipment.edit")
    if not values.get("buyer_id"):
        raise ValidationError("Buyer is required", key="error.buyer_required")
    shipment_id = values.get("id")
    if shipment_id:
        shipment = get_shipment(session, shipment_id)
        action = "update"
    else:
        shipment = Shipment(
            number=values.get("number")
            or quotation_service.next_number(session, "SH", Shipment, Shipment.number),
            buyer_id=values["buyer_id"],
        )
        session.add(shipment)
        action = "create"

    for key in (
        "buyer_id",
        "lead_id",
        "contract_id",
        "quotation_id",
        "incoterm",
        "origin",
        "loading_port",
        "destination",
        "container_type",
        "forwarder",
        "carrier",
        "tracking_reference",
        "etd",
        "eta",
        "actual_departure",
        "actual_arrival",
        "customs_status",
        "currency",
        "planned_freight_cost",
        "freight_cost",
        "planned_insurance_cost",
        "insurance_cost",
        "other_cost",
        "notes",
    ):
        if key in values:
            setattr(shipment, key, values[key])
    if shipment.etd and shipment.eta and shipment.eta < shipment.etd:
        raise ValidationError("ETA is before ETD", key="error.date_range")
    session.flush()

    if items is not None:
        for item in list(shipment.items):
            session.delete(item)
        session.flush()
        for order, item in enumerate(items):
            session.add(
                ShipmentItem(
                    shipment_id=shipment.id,
                    product_id=item.get("product_id"),
                    description=item.get("description") or "",
                    hs_code=item.get("hs_code"),
                    quantity=float(item.get("quantity") or 0),
                    unit=item.get("unit") or "pcs",
                    unit_price=float(item.get("unit_price") or 0),
                    packages=float(item.get("packages") or 0),
                    net_weight=float(item.get("net_weight") or 0),
                    gross_weight=float(item.get("gross_weight") or 0),
                    sort_order=order,
                )
            )
        session.flush()
        # The cached collection is stale after the delete/insert cycle.
        session.expire(shipment, ["items"])
        recalculate_totals(session, shipment.id)

    audit_service.record(
        session,
        action=action,
        entity_type="shipment",
        entity_id=shipment.id,
        summary=f"Shipment {shipment.number} {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    return shipment


def recalculate_totals(session: Session, shipment_id: int) -> Shipment:
    """Roll package count and weights up from the item lines."""
    shipment = get_shipment(session, shipment_id)
    shipment.package_count = round(sum(item.packages for item in shipment.items), 2)
    shipment.net_weight = round(sum(item.net_weight for item in shipment.items), 2)
    shipment.gross_weight = round(sum(item.gross_weight for item in shipment.items), 2)
    session.flush()
    return shipment


def build_items_from_quotation(session: Session, quotation_id: int) -> list[dict]:
    """Derive shipment lines (with packing data) from a quotation."""
    data = quotation_service.quotation_dict(session, quotation_id)
    items: list[dict] = []
    for line in data["items"]:
        product = session.get(Product, line["product_id"]) if line["product_id"] else None
        quantity = float(line["quantity"] or 0)
        units_per_carton = float(product.units_per_carton or 0) if product else 0
        packages = round(quantity / units_per_carton, 2) if units_per_carton else 0.0
        items.append(
            {
                "product_id": line["product_id"],
                "description": line["description"],
                "hs_code": line["hs_code"],
                "quantity": quantity,
                "unit": line["unit"],
                "unit_price": line["unit_price"],
                "packages": packages,
                "net_weight": (
                    round(quantity * float(product.net_weight or 0), 2) if product else 0.0
                ),
                "gross_weight": (
                    round(quantity * float(product.gross_weight or 0), 2) if product else 0.0
                ),
            }
        )
    return items


def can_transition(current: str, target: str) -> bool:
    """True when the shipment status transition is allowed."""
    if current == target:
        return True
    return target in SHIPMENT_TRANSITIONS.get(current, ())


def change_status(
    session: Session, actor: CurrentUser, shipment_id: int, new_status: str
) -> Shipment:
    """Apply a validated shipment status transition."""
    actor.require("shipment.edit")
    shipment = get_shipment(session, shipment_id)
    previous = shipment.status
    if not can_transition(previous, new_status):
        raise WorkflowError(
            f"Transition {previous} -> {new_status} is not allowed",
            key="error.shipment_transition",
            source=previous,
            target=new_status,
        )
    shipment.status = new_status
    if new_status == "in_transit" and not shipment.actual_departure:
        shipment.actual_departure = today()
    if new_status in ("arrived", "delivered") and not shipment.actual_arrival:
        shipment.actual_arrival = today()
    session.flush()
    audit_service.record(
        session,
        action="status_change",
        entity_type="shipment",
        entity_id=shipment.id,
        summary=f"Shipment {shipment.number}: {previous} -> {new_status}",
        user_id=actor.id,
        username=actor.username,
    )
    if shipment.lead_id:
        audit_service.add_activity(
            session,
            entity_type="lead",
            entity_id=shipment.lead_id,
            kind="shipment",
            title=f"Shipment {shipment.number}: {new_status}",
            user_id=actor.id,
        )
    return shipment


def save_freight_quote(session: Session, actor: CurrentUser, values: dict) -> FreightQuote:
    """Add or update a forwarder offer."""
    actor.require("shipment.edit")
    quote_id = values.get("id")
    if quote_id:
        quote = session.get(FreightQuote, quote_id)
        if quote is None:
            raise NotFoundError("Freight quote not found")
    else:
        quote = FreightQuote(
            shipment_id=values["shipment_id"], forwarder=values.get("forwarder") or ""
        )
        session.add(quote)
    for key in (
        "shipment_id",
        "forwarder",
        "mode",
        "currency",
        "price",
        "transit_days",
        "valid_until",
        "notes",
    ):
        if key in values:
            setattr(quote, key, values[key])
    session.flush()
    return quote


def select_freight_quote(session: Session, actor: CurrentUser, quote_id: int) -> FreightQuote:
    """Choose one forwarder offer and copy its price into the shipment budget."""
    actor.require("shipment.edit")
    quote = session.get(FreightQuote, quote_id)
    if quote is None:
        raise NotFoundError("Freight quote not found")
    for sibling in quote.shipment.freight_quotes:
        sibling.is_selected = 1 if sibling.id == quote_id else 0
    quote.shipment.planned_freight_cost = quote.price
    quote.shipment.forwarder = quote.forwarder
    session.flush()
    return quote


def delete_freight_quote(session: Session, actor: CurrentUser, quote_id: int) -> None:
    """Remove a forwarder offer."""
    actor.require("shipment.edit")
    quote = session.get(FreightQuote, quote_id)
    if quote is not None:
        session.delete(quote)
        session.flush()


def delay_alerts(session: Session) -> list[dict]:
    """Shipments whose ETD or ETA has passed without the matching actual date."""
    rows = (
        session.scalars(
            select(Shipment).where(
                Shipment.is_archived.is_(False),
                Shipment.status.not_in(("delivered", "cancelled")),
            )
        )
        .unique()
        .all()
    )
    alerts: list[dict] = []
    for shipment in rows:
        if shipment.etd and shipment.etd < today() and not shipment.actual_departure:
            alerts.append(
                {
                    "id": shipment.id,
                    "number": shipment.number,
                    "kind": "etd",
                    "planned": shipment.etd,
                    "days": (today() - shipment.etd).days,
                }
            )
        if shipment.eta and shipment.eta < today() and not shipment.actual_arrival:
            alerts.append(
                {
                    "id": shipment.id,
                    "number": shipment.number,
                    "kind": "eta",
                    "planned": shipment.eta,
                    "days": (today() - shipment.eta).days,
                }
            )
    return alerts


def archive_shipment(session: Session, actor: CurrentUser, shipment_id: int) -> None:
    """Soft delete a shipment."""
    actor.require("shipment.edit")
    shipment = get_shipment(session, shipment_id)
    shipment.is_archived = True
    session.flush()
