"""Purchase requests, supplier quotes and purchase orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.database.session import session_scope
from app.models.entities import PurchaseRequest, User
from app.models.enums import OrderStatus, PurchaseStatus
from app.repositories import Repositories
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, require


class PurchaseRuleError(Exception):
    """Raised when a business rule blocks the operation; carries an i18n key."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


@dataclass
class QuoteRow:
    """Supplier offer with its computed total cost of ownership."""

    id: int
    supplier_id: int | None
    supplier_name: str
    contact: str
    unit_price: float
    delivery_cost: float
    delivery_days: int
    payment_terms: str
    file_path: str
    is_selected: bool
    total_value: float
    is_cheapest: bool = False
    is_fastest: bool = False
    is_best: bool = False


def list_requests(
    project_id: int | None = None,
    status: str = "",
    text: str = "",
    include_archived: bool = False,
) -> list[dict]:
    """Return purchase requests as table rows."""
    with session_scope() as session:
        repos = Repositories(session)
        filters = []
        if project_id:
            filters.append(PurchaseRequest.project_id == project_id)
        if status:
            filters.append(PurchaseRequest.status == status)
        if text:
            filters.append(PurchaseRequest.title.ilike(f"%{text}%"))
        rows = []
        for req in repos.requests.list(
            filters=filters,
            order_by=PurchaseRequest.created_at.desc(),
            include_archived=include_archived,
        ):
            quotes = repos.quotes.for_request(req.id)
            selected = next((q for q in quotes if q.is_selected), None)
            rows.append(
                {
                    "id": req.id,
                    "number": req.number,
                    "project_id": req.project_id,
                    "project": req.project.name if req.project else "",
                    "estimate_item_id": req.estimate_item_id,
                    "estimate_item": req.estimate_item.name if req.estimate_item else "",
                    "off_estimate": req.off_estimate,
                    "title": req.title,
                    "unit": req.unit,
                    "quantity": req.quantity,
                    "est_price": req.est_price,
                    "est_total": req.est_total,
                    "needed_date": req.needed_date,
                    "delivery_address": req.delivery_address,
                    "responsible": req.responsible.label if req.responsible else "",
                    "responsible_id": req.responsible_id,
                    "status": req.status,
                    "note": req.note,
                    "quotes_count": len(quotes),
                    "selected_supplier": (
                        selected.supplier.name
                        if selected and selected.supplier
                        else (selected.supplier_name if selected else "")
                    ),
                    "selected_total": selected.total_value(req.quantity) if selected else 0.0,
                    "is_archived": req.is_archived,
                }
            )
        return rows


def get_request(request_id: int) -> dict:
    """Return one purchase request as a dictionary."""
    rows = [r for r in list_requests() if r["id"] == request_id]
    if not rows:
        raise LookupError(f"PurchaseRequest #{request_id} not found")
    return rows[0]


def save_request(data: dict, actor: CurrentUser, request_id: int | None = None) -> int:
    """Create or update a purchase request.

    Business rule: a request must reference an estimate item unless it is
    explicitly flagged as an off-estimate purchase.
    """
    require(actor.role_code, Perm.PURCHASE_EDIT)
    if not data.get("estimate_item_id") and not data.get("off_estimate"):
        raise PurchaseRuleError("estimate_item_required")
    with session_scope() as session:
        repos = Repositories(session)
        db_actor = session.get(User, actor.id)
        if request_id:
            request = repos.requests.get_or_raise(request_id)
            repos.requests.update(request, **data)
            action = audit_service.Action.UPDATE
        else:
            data.setdefault("number", repos.requests.next_number())
            request = repos.requests.create(**data)
            action = audit_service.Action.CREATE
        audit_service.log(
            session,
            user=db_actor,
            action=action,
            entity_type="PurchaseRequest",
            entity_id=request.id,
            project_id=request.project_id,
            description=f"{request.number} {request.title}",
            new_value=f"{request.quantity} x {request.est_price}",
        )
        return request.id


def set_request_status(request_id: int, status: str, actor: CurrentUser) -> None:
    """Change the workflow status of a request."""
    if status in (PurchaseStatus.APPROVED.value, PurchaseStatus.REJECTED.value):
        require(actor.role_code, Perm.PURCHASE_APPROVE)
    else:
        require(actor.role_code, Perm.PURCHASE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        request = repos.requests.get_or_raise(request_id)
        old = request.status
        request.status = status
        action = {
            PurchaseStatus.APPROVED.value: audit_service.Action.APPROVE,
            PurchaseStatus.REJECTED.value: audit_service.Action.REJECT,
        }.get(status, audit_service.Action.UPDATE)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=action,
            entity_type="PurchaseRequest",
            entity_id=request_id,
            project_id=request.project_id,
            description=f"{request.number} {request.title}",
            old_value=old,
            new_value=status,
        )


def archive_request(request_id: int, actor: CurrentUser, archived: bool = True) -> None:
    """Archive or restore a request."""
    require(actor.role_code, Perm.PURCHASE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        request = repos.requests.get_or_raise(request_id)
        repos.requests.archive(request, archived)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.ARCHIVE,
            entity_type="PurchaseRequest",
            entity_id=request_id,
            project_id=request.project_id,
            description=request.title,
            new_value=str(archived),
        )


# --------------------------------------------------------------------------- #
# Quotes
# --------------------------------------------------------------------------- #


def list_quotes(request_id: int) -> list[QuoteRow]:
    """Return the quotes of a request, flagged with cheapest/fastest/best."""
    with session_scope() as session:
        repos = Repositories(session)
        request = repos.requests.get_or_raise(request_id)
        rows = [
            QuoteRow(
                id=q.id,
                supplier_id=q.supplier_id,
                supplier_name=q.supplier.name if q.supplier else q.supplier_name,
                contact=q.contact or "",
                unit_price=q.unit_price or 0.0,
                delivery_cost=q.delivery_cost or 0.0,
                delivery_days=q.delivery_days or 0,
                payment_terms=q.payment_terms or "",
                file_path=q.file_path or "",
                is_selected=q.is_selected,
                total_value=q.total_value(request.quantity),
            )
            for q in repos.quotes.for_request(request_id)
        ]
        return _rank_quotes(rows, request.needed_date)


def _rank_quotes(rows: list[QuoteRow], needed_date: date | None = None) -> list[QuoteRow]:
    """Flag the cheapest, fastest and overall best offer.

    "Best" balances total value and lead time: each quote gets a normalized
    score ``0.7 * price_score + 0.3 * time_score`` (lower is better).
    """
    if not rows:
        return rows
    min_total = min(r.total_value for r in rows) or 1.0
    max_total = max(r.total_value for r in rows)
    min_days = min(r.delivery_days for r in rows)
    max_days = max(r.delivery_days for r in rows)
    for row in rows:
        row.is_cheapest = row.total_value == min_total
        row.is_fastest = row.delivery_days == min_days
    span_total = (max_total - min_total) or 1.0
    span_days = (max_days - min_days) or 1.0
    best, best_score = None, None
    for row in rows:
        price_score = (row.total_value - min_total) / span_total
        time_score = (row.delivery_days - min_days) / span_days
        score = 0.7 * price_score + 0.3 * time_score
        if best_score is None or score < best_score:
            best, best_score = row, score
    if best is not None:
        best.is_best = True
    return sorted(rows, key=lambda r: r.total_value)


def save_quote(request_id: int, data: dict, actor: CurrentUser, quote_id: int | None = None) -> int:
    """Create or update a supplier quote."""
    require(actor.role_code, Perm.PURCHASE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        request = repos.requests.get_or_raise(request_id)
        if quote_id:
            quote = repos.quotes.get_or_raise(quote_id)
            repos.quotes.update(quote, **data)
        else:
            quote = repos.quotes.create(request_id=request_id, **data)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.UPDATE if quote_id else audit_service.Action.CREATE,
            entity_type="SupplierQuote",
            entity_id=quote.id,
            project_id=request.project_id,
            description=f"{request.number}: {quote.supplier_name or quote.supplier_id}",
        )
        return quote.id


def delete_quote(quote_id: int, actor: CurrentUser) -> None:
    """Remove a supplier quote."""
    require(actor.role_code, Perm.PURCHASE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        quote = repos.quotes.get_or_raise(quote_id)
        repos.quotes.delete(quote)


def select_quote(quote_id: int, actor: CurrentUser) -> None:
    """Mark one quote as the winning offer."""
    require(actor.role_code, Perm.PURCHASE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        quote = repos.quotes.get_or_raise(quote_id)
        for other in repos.quotes.for_request(quote.request_id):
            other.is_selected = other.id == quote_id
        request = repos.requests.get_or_raise(quote.request_id)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.UPDATE,
            entity_type="SupplierQuote",
            entity_id=quote_id,
            project_id=request.project_id,
            description=f"selected quote for {request.number}",
        )


# --------------------------------------------------------------------------- #
# Orders
# --------------------------------------------------------------------------- #


def create_order(request_id: int, actor: CurrentUser, note: str = "") -> int:
    """Create a purchase order from the selected quote."""
    require(actor.role_code, Perm.PURCHASE_APPROVE)
    with session_scope() as session:
        repos = Repositories(session)
        request = repos.requests.get_or_raise(request_id)
        quote = next((q for q in repos.quotes.for_request(request_id) if q.is_selected), None)
        if quote is None:
            raise PurchaseRuleError("no_quote_selected")
        order = repos.orders.create(
            order_no=repos.orders.next_number(),
            request_id=request_id,
            quote_id=quote.id,
            supplier_id=quote.supplier_id,
            order_date=date.today(),
            total_amount=quote.total_value(request.quantity),
            status=OrderStatus.NEW.value,
            note=note,
        )
        request.status = PurchaseStatus.ORDERED.value
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.CREATE,
            entity_type="PurchaseOrder",
            entity_id=order.id,
            project_id=request.project_id,
            description=f"{order.order_no} ({request.title})",
            new_value=str(order.total_amount),
        )
        return order.id


def list_orders(project_id: int | None = None) -> list[dict]:
    """Return purchase orders as table rows."""
    with session_scope() as session:
        repos = Repositories(session)
        rows = []
        for order in repos.orders.list():
            request = order.request
            if project_id and (request is None or request.project_id != project_id):
                continue
            rows.append(
                {
                    "id": order.id,
                    "order_no": order.order_no,
                    "order_date": order.order_date,
                    "request_id": order.request_id,
                    "title": request.title if request else "",
                    "project": request.project.name if request and request.project else "",
                    "project_id": request.project_id if request else None,
                    "supplier": order.supplier.name if order.supplier else "",
                    "quantity": request.quantity if request else 0.0,
                    "unit": request.unit if request else "",
                    "total_amount": order.total_amount,
                    "status": order.status,
                    "note": order.note or "",
                }
            )
        return rows


def set_order_status(order_id: int, status: str, actor: CurrentUser) -> None:
    """Update the delivery status of an order."""
    require(actor.role_code, Perm.PURCHASE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        order = repos.orders.get_or_raise(order_id)
        old = order.status
        order.status = status
        if status == OrderStatus.DELIVERED.value and order.request:
            order.request.status = PurchaseStatus.COMPLETED.value
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.UPDATE,
            entity_type="PurchaseOrder",
            entity_id=order_id,
            project_id=order.request.project_id if order.request else None,
            description=order.order_no,
            old_value=old,
            new_value=status,
        )


def order_document(order_id: int) -> dict:
    """Return everything needed to render the purchase order PDF."""
    with session_scope() as session:
        repos = Repositories(session)
        order = repos.orders.get_or_raise(order_id)
        request = order.request
        quote = order.quote
        return {
            "order_no": order.order_no,
            "order_date": order.order_date,
            "supplier": order.supplier.name if order.supplier else "",
            "supplier_phone": order.supplier.phone if order.supplier else "",
            "supplier_address": order.supplier.address if order.supplier else "",
            "project": request.project.name if request and request.project else "",
            "delivery_address": request.delivery_address if request else "",
            "title": request.title if request else "",
            "unit": request.unit if request else "",
            "quantity": request.quantity if request else 0.0,
            "unit_price": quote.unit_price if quote else 0.0,
            "delivery_cost": quote.delivery_cost if quote else 0.0,
            "delivery_days": quote.delivery_days if quote else 0,
            "payment_terms": quote.payment_terms if quote else "",
            "total_amount": order.total_amount,
            "note": order.note or "",
        }
