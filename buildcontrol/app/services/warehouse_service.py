"""Material catalogue and warehouse stock movements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database.session import session_scope
from app.models.entities import Material, User, WarehouseTransaction
from app.models.enums import TxKind
from app.repositories import Repositories
from app.services import audit_service, estimate_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, require

#: Kinds that increase the stock balance.
POSITIVE_KINDS = (TxKind.IN.value, TxKind.RETURN.value, TxKind.ADJUST.value)


class StockError(Exception):
    """Raised when a movement would break stock integrity; carries an i18n key."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


@dataclass
class StockRow:
    """Catalogue row enriched with the computed balance."""

    id: int
    sku: str
    name: str
    category: str
    unit: str
    min_stock: float
    standard_price: float
    supplier: str
    supplier_id: int | None
    balance: float
    value: float
    is_low: bool
    note: str
    is_archived: bool


def balance_of(session: Session, material_id: int) -> float:
    """Return the current stock balance of a material.

    ``SUM`` is executed with an explicit CASE so receipts, returns and
    adjustments add while issues and losses subtract.
    """
    signed = case(
        (WarehouseTransaction.kind.in_(POSITIVE_KINDS), WarehouseTransaction.quantity),
        else_=-WarehouseTransaction.quantity,
    )
    value = session.scalar(
        select(func.sum(signed)).where(WarehouseTransaction.material_id == material_id)
    )
    return round(float(value or 0.0), 3)


def list_materials(
    text: str = "",
    category: str = "",
    only_low: bool = False,
    include_archived: bool = False,
) -> list[StockRow]:
    """Return the material catalogue with balances."""
    with session_scope() as session:
        repos = Repositories(session)
        filters = []
        if text:
            pattern = f"%{text}%"
            filters.append(Material.name.ilike(pattern) | Material.sku.ilike(pattern))
        if category:
            filters.append(Material.category == category)
        rows: list[StockRow] = []
        for material in repos.materials.list(
            filters=filters, order_by=Material.name, include_archived=include_archived
        ):
            balance = balance_of(session, material.id)
            is_low = balance < (material.min_stock or 0.0)
            if only_low and not is_low:
                continue
            rows.append(
                StockRow(
                    id=material.id,
                    sku=material.sku,
                    name=material.name,
                    category=material.category or "",
                    unit=material.unit,
                    min_stock=material.min_stock or 0.0,
                    standard_price=material.standard_price or 0.0,
                    supplier=material.supplier.name if material.supplier else "",
                    supplier_id=material.supplier_id,
                    balance=balance,
                    value=round(balance * (material.standard_price or 0.0), 2),
                    is_low=is_low,
                    note=material.note or "",
                    is_archived=material.is_archived,
                )
            )
        return rows


def material_choices() -> list[tuple[int | str, str]]:
    """Return ``[(id, label)]`` pairs for material pickers."""
    with session_scope() as session:
        rows = [
            (m.id, f"{m.sku} — {m.name}")
            for m in Repositories(session).materials.list(order_by=Material.name)
        ]
    return [("", "—")] + rows


def save_material(data: dict, actor: CurrentUser, material_id: int | None = None) -> int:
    """Create or update a catalogue entry."""
    require(actor.role_code, Perm.WAREHOUSE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        if material_id:
            material = repos.materials.get_or_raise(material_id)
            repos.materials.update(material, **data)
            action = audit_service.Action.UPDATE
        else:
            existing = repos.materials.by_sku(str(data.get("sku") or ""))
            if existing is not None:
                raise StockError("sku_exists")
            material = repos.materials.create(**data)
            action = audit_service.Action.CREATE
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=action,
            entity_type="Material",
            entity_id=material.id,
            description=f"{material.sku} {material.name}",
        )
        return material.id


def archive_material(material_id: int, actor: CurrentUser, archived: bool = True) -> None:
    """Archive or restore a catalogue entry."""
    require(actor.role_code, Perm.WAREHOUSE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        material = repos.materials.get_or_raise(material_id)
        repos.materials.archive(material, archived)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.ARCHIVE,
            entity_type="Material",
            entity_id=material_id,
            description=material.name,
            new_value=str(archived),
        )


def list_transactions(
    project_id: int | None = None,
    material_id: int | None = None,
    kind: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    """Return stock movements as table rows."""
    with session_scope() as session:
        repos = Repositories(session)
        filters = []
        if project_id:
            filters.append(WarehouseTransaction.project_id == project_id)
        if material_id:
            filters.append(WarehouseTransaction.material_id == material_id)
        if kind:
            filters.append(WarehouseTransaction.kind == kind)
        if date_from:
            filters.append(WarehouseTransaction.tx_date >= date_from)
        if date_to:
            filters.append(WarehouseTransaction.tx_date <= date_to)
        rows = []
        for tx in repos.stock.list(filters=filters, order_by=WarehouseTransaction.tx_date.desc()):
            rows.append(
                {
                    "id": tx.id,
                    "tx_date": tx.tx_date,
                    "kind": tx.kind,
                    "material_id": tx.material_id,
                    "material": tx.material.name if tx.material else "",
                    "sku": tx.material.sku if tx.material else "",
                    "unit": tx.material.unit if tx.material else "",
                    "quantity": tx.quantity,
                    "signed_quantity": tx.signed_quantity,
                    "unit_price": tx.unit_price,
                    "total": tx.total,
                    "project": tx.project.name if tx.project else "",
                    "project_id": tx.project_id,
                    "estimate_item": tx.estimate_item.name if tx.estimate_item else "",
                    "estimate_item_id": tx.estimate_item_id,
                    "user": tx.user.label if tx.user else "",
                    "doc_path": tx.doc_path or "",
                    "note": tx.note or "",
                }
            )
        return rows


def register_transaction(data: dict, actor: CurrentUser) -> int:
    """Register a stock movement and refresh the affected estimate actuals.

    Issues, losses and negative adjustments are rejected when the balance is
    insufficient, so the stock can never go negative.
    """
    require(actor.role_code, Perm.WAREHOUSE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        material_id = int(data["material_id"])
        quantity = float(data.get("quantity") or 0.0)
        kind = str(data.get("kind") or TxKind.IN.value)
        if quantity <= 0:
            raise StockError("quantity_positive")
        if kind not in POSITIVE_KINDS and balance_of(session, material_id) < quantity:
            raise StockError("not_enough_stock")
        tx = repos.stock.create(user_id=actor.id, **data)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.STOCK,
            entity_type="WarehouseTransaction",
            entity_id=tx.id,
            project_id=tx.project_id,
            description=f"{kind}: {tx.material.name if tx.material else material_id}",
            new_value=f"{quantity} x {tx.unit_price}",
        )
        if tx.project_id:
            estimate_service.recalc_item_actuals(session, tx.project_id)
        return tx.id


def delete_transaction(tx_id: int, actor: CurrentUser) -> None:
    """Remove a stock movement (admin correction) and recalculate actuals."""
    require(actor.role_code, Perm.WAREHOUSE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        tx = repos.stock.get_or_raise(tx_id)
        project_id = tx.project_id
        repos.stock.delete(tx)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.DELETE,
            entity_type="WarehouseTransaction",
            entity_id=tx_id,
            project_id=project_id,
            description="stock movement removed",
        )
        if project_id:
            estimate_service.recalc_item_actuals(session, project_id)


def low_stock() -> list[StockRow]:
    """Return materials whose balance dropped below the minimum."""
    return list_materials(only_low=True)


def categories() -> list[str]:
    """Return the distinct material categories present in the catalogue."""
    with session_scope() as session:
        rows = session.scalars(
            select(Material.category).where(Material.category != "").distinct()
        ).all()
        return sorted(str(r) for r in rows)
