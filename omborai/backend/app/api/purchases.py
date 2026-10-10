import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import Principal, get_principal, require_roles
from ..models import Purchase, PurchaseItem
from ..schemas import PurchaseIn, PurchaseItemOut, PurchaseOut
from ..services.stock import get_store, record_movement

router = APIRouter(prefix="/purchases", tags=["purchases"])

ROLES = ("owner", "manager", "warehouse")


def _to_out(purchase: Purchase, items: list[PurchaseItem]) -> PurchaseOut:
    return PurchaseOut(
        id=purchase.id,
        store_id=purchase.store_id,
        supplier_id=purchase.supplier_id,
        note=purchase.note,
        total_cost=purchase.total_cost,
        created_at=purchase.created_at,
        items=[PurchaseItemOut(product_id=i.product_id, qty=i.qty, unit_cost=i.unit_cost) for i in items],
    )


@router.post("", status_code=201, response_model=PurchaseOut)
async def create_purchase(
    body: PurchaseIn,
    principal: Principal = Depends(require_roles(*ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOut:
    """Kirim hujjati: hujjat, qatorlar va har bir qator uchun 'receipt' harakati bitta tranzaksiyada."""
    await get_store(session, body.store_id)

    purchase = Purchase(
        tenant_id=principal.tenant_id,
        store_id=body.store_id,
        supplier_id=body.supplier_id,
        created_by=principal.user_id,
        note=body.note,
    )
    session.add(purchase)
    await session.flush()

    items: list[PurchaseItem] = []
    total = Decimal(0)
    for line in body.items:
        item = PurchaseItem(
            tenant_id=principal.tenant_id,
            purchase_id=purchase.id,
            product_id=line.product_id,
            qty=line.qty,
            unit_cost=line.unit_cost,
        )
        session.add(item)
        items.append(item)
        total += line.qty * line.unit_cost
        await record_movement(
            session,
            tenant_id=principal.tenant_id,
            store_id=body.store_id,
            product_id=line.product_id,
            qty=line.qty,
            kind="receipt",
            created_by=principal.user_id,
            reference_type="purchase",
            reference_id=purchase.id,
        )

    purchase.total_cost = int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    await session.flush()
    await session.commit()
    return _to_out(purchase, items)


@router.get("", response_model=list[PurchaseOut])
async def list_purchases(
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> list[PurchaseOut]:
    rows = await session.execute(select(Purchase).order_by(Purchase.created_at.desc()).limit(100))
    purchases = list(rows.scalars().all())
    if not purchases:
        return []
    item_rows = await session.execute(
        select(PurchaseItem).where(PurchaseItem.purchase_id.in_([p.id for p in purchases]))
    )
    by_purchase: dict[uuid.UUID, list[PurchaseItem]] = {}
    for item in item_rows.scalars().all():
        by_purchase.setdefault(item.purchase_id, []).append(item)
    return [_to_out(p, by_purchase.get(p.id, [])) for p in purchases]
