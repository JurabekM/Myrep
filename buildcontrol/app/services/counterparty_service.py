"""Suppliers and contractors, including the performance rating."""

from __future__ import annotations

from app.database.session import session_scope
from app.models.entities import Counterparty, User
from app.models.enums import CounterpartyKind
from app.repositories import Repositories
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, require


def compute_rating(
    *,
    delay_days: int,
    contract_amount: float,
    paid_amount: float,
    quality_score: float,
    disputes: int,
) -> float:
    """Return a 0..5 contractor rating.

    The score combines four weighted components:

    * on-time delivery (40%) — loses a point per 10 days of delay;
    * price discipline (20%) — penalises payments above the contract value;
    * quality (30%) — the manual 0..5 quality assessment;
    * disputes (10%) — half a point off per registered dispute.
    """
    timeliness = max(0.0, 5.0 - (max(0, delay_days) / 10.0))
    if contract_amount > 0:
        overrun = max(0.0, (paid_amount - contract_amount) / contract_amount)
        price = max(0.0, 5.0 - overrun * 10.0)
    else:
        price = 5.0
    quality = min(5.0, max(0.0, quality_score))
    dispute_score = max(0.0, 5.0 - 0.5 * max(0, disputes))
    rating = 0.4 * timeliness + 0.2 * price + 0.3 * quality + 0.1 * dispute_score
    return round(min(5.0, max(0.0, rating)), 2)


def list_counterparties(
    kind: str = "",
    text: str = "",
    include_archived: bool = False,
) -> list[dict]:
    """Return counterparties as table rows."""
    with session_scope() as session:
        repos = Repositories(session)
        filters = []
        if kind:
            filters.append(Counterparty.kind == kind)
        if text:
            pattern = f"%{text}%"
            filters.append(
                Counterparty.name.ilike(pattern)
                | Counterparty.phone.ilike(pattern)
                | Counterparty.category.ilike(pattern)
            )
        rows = []
        for cp in repos.counterparties.list(
            filters=filters, order_by=Counterparty.name, include_archived=include_archived
        ):
            rows.append(
                {
                    "id": cp.id,
                    "kind": cp.kind,
                    "name": cp.name,
                    "tin": cp.tin or "",
                    "phone": cp.phone or "",
                    "email": cp.email or "",
                    "address": cp.address or "",
                    "bank_details": cp.bank_details or "",
                    "category": cp.category or "",
                    "rating": cp.rating or 0.0,
                    "contract_amount": cp.contract_amount or 0.0,
                    "paid_amount": cp.paid_amount or 0.0,
                    "completed_work": cp.completed_work or 0.0,
                    "delay_days": cp.delay_days or 0,
                    "quality_score": cp.quality_score or 0.0,
                    "disputes": cp.disputes or 0,
                    "note": cp.note or "",
                    "is_archived": cp.is_archived,
                }
            )
        return rows


def counterparty_choices(kind: str = "") -> list[tuple[int | str, str]]:
    """Return ``[(id, name)]`` pairs for counterparty pickers."""
    rows = [(row["id"], row["name"]) for row in list_counterparties(kind=kind)]
    return [("", "—")] + rows


def save_counterparty(data: dict, actor: CurrentUser, cp_id: int | None = None) -> int:
    """Create or update a counterparty; the rating is recomputed on save."""
    require(actor.role_code, Perm.COUNTERPARTY_EDIT)
    data = dict(data)
    data["rating"] = compute_rating(
        delay_days=int(data.get("delay_days") or 0),
        contract_amount=float(data.get("contract_amount") or 0.0),
        paid_amount=float(data.get("paid_amount") or 0.0),
        quality_score=float(data.get("quality_score") or 0.0),
        disputes=int(data.get("disputes") or 0),
    )
    with session_scope() as session:
        repos = Repositories(session)
        if cp_id:
            cp = repos.counterparties.get_or_raise(cp_id)
            repos.counterparties.update(cp, **data)
            action = audit_service.Action.UPDATE
        else:
            data.setdefault("kind", CounterpartyKind.SUPPLIER.value)
            cp = repos.counterparties.create(**data)
            action = audit_service.Action.CREATE
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=action,
            entity_type="Counterparty",
            entity_id=cp.id,
            description=f"{cp.kind}: {cp.name}",
        )
        return cp.id


def archive_counterparty(cp_id: int, actor: CurrentUser, archived: bool = True) -> None:
    """Archive or restore a counterparty."""
    require(actor.role_code, Perm.COUNTERPARTY_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        cp = repos.counterparties.get_or_raise(cp_id)
        repos.counterparties.archive(cp, archived)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.ARCHIVE,
            entity_type="Counterparty",
            entity_id=cp_id,
            description=cp.name,
            new_value=str(archived),
        )


def contractor_performance() -> list[dict]:
    """Return contractor rows sorted by rating (used by the report)."""
    rows = list_counterparties(kind=CounterpartyKind.CONTRACTOR.value)
    for row in rows:
        contract = row["contract_amount"] or 0.0
        row["paid_ratio"] = round(row["paid_amount"] / contract * 100, 1) if contract else 0.0
    return sorted(rows, key=lambda r: r["rating"], reverse=True)
