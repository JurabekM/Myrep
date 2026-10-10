import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import Principal, get_principal, require_roles
from ..errors import ProblemError
from ..models import Product, StockMovement
from ..schemas import BalanceOut, MovementIn, MovementOut
from ..services.stock import get_store, record_movement

router = APIRouter(prefix="/stock", tags=["stock"])

ROLES = ("owner", "manager", "warehouse")


@router.post("/movements", status_code=201, response_model=MovementOut)
async def create_movement(
    body: MovementIn,
    principal: Principal = Depends(require_roles(*ROLES)),
    session: AsyncSession = Depends(get_db),
) -> StockMovement:
    """Qo'lda harakat: tuzatish (adjustment) yoki yo'qotish/buzilish (writeoff)."""
    await get_store(session, body.store_id)

    if body.kind == "writeoff":
        if body.qty <= 0:
            raise ProblemError(422, "Yo'qotish miqdori musbat bo'lishi kerak")
        qty = -body.qty
    else:
        qty = body.qty
        if qty == 0:
            raise ProblemError(422, "Tuzatish miqdori noldan farqli bo'lishi kerak")

    movement = await record_movement(
        session,
        tenant_id=principal.tenant_id,
        store_id=body.store_id,
        product_id=body.product_id,
        qty=qty,
        kind=body.kind,
        created_by=principal.user_id,
        note=body.note,
    )
    await session.commit()
    return movement


@router.get("/movements", response_model=list[MovementOut])
async def list_movements(
    store_id: uuid.UUID,
    product_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> list[StockMovement]:
    stmt = select(StockMovement).where(StockMovement.store_id == store_id)
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    rows = await session.execute(stmt.order_by(StockMovement.created_at.desc()).limit(limit))
    return list(rows.scalars().all())


@router.get("/balances", response_model=list[BalanceOut])
async def list_balances(
    store_id: uuid.UUID,
    low_only: bool = False,
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> list[BalanceOut]:
    """Filial bo'yicha qoldiq. low_only=true — faqat minimal chegaradan past tovarlar."""
    await get_store(session, store_id)
    bal = (
        select(StockMovement.product_id, func.sum(StockMovement.qty).label("qty"))
        .where(StockMovement.store_id == store_id)
        .group_by(StockMovement.product_id)
        .subquery()
    )
    qty = func.coalesce(bal.c.qty, 0)
    stmt = (
        select(Product, qty)
        .outerjoin(bal, bal.c.product_id == Product.id)
        .where(Product.deleted_at.is_(None), Product.is_active.is_(True))
        .order_by(Product.name)
    )
    if low_only:
        stmt = stmt.where(qty < Product.min_stock)

    rows = await session.execute(stmt)
    return [
        BalanceOut(
            product_id=p.id,
            name=p.name,
            unit=p.unit,
            qty=q,
            min_stock=p.min_stock,
            low=q < p.min_stock,
        )
        for p, q in rows.all()
    ]
