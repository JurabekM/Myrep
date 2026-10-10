"""Qoldiq ledger'i bilan ishlash.

Qoldiq hech qachon alohida ustunda saqlanmaydi: u har doim stock_movements yig'indisi.
Bir vaqtda ikki sotuv bitta tovarning oxirgi donasini olib ketmasligi uchun
harakat yozishdan oldin tovar qatori SELECT ... FOR UPDATE bilan qulflanadi.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ProblemError
from ..models import Product, StockMovement, Store


async def get_store(session: AsyncSession, store_id: uuid.UUID) -> Store:
    store = await session.scalar(select(Store).where(Store.id == store_id, Store.deleted_at.is_(None)))
    if store is None:
        raise ProblemError(404, "Filial topilmadi")
    return store


async def lock_product(session: AsyncSession, product_id: uuid.UUID) -> Product:
    product = await session.scalar(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)).with_for_update()
    )
    if product is None:
        raise ProblemError(404, "Tovar topilmadi")
    return product


async def balance(session: AsyncSession, store_id: uuid.UUID, product_id: uuid.UUID) -> Decimal:
    value = await session.scalar(
        select(func.coalesce(func.sum(StockMovement.qty), 0)).where(
            StockMovement.store_id == store_id,
            StockMovement.product_id == product_id,
        )
    )
    return Decimal(value or 0)


async def record_movement(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    qty: Decimal,
    kind: str,
    created_by: uuid.UUID,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    note: str | None = None,
    allow_negative: bool = False,
) -> StockMovement:
    if qty == 0:
        raise ProblemError(422, "Miqdor noldan farqli bo'lishi kerak")

    await lock_product(session, product_id)
    current = await balance(session, store_id, product_id)
    if not allow_negative and current + qty < 0:
        raise ProblemError(
            409,
            "Qoldiq yetarli emas",
            f"Joriy qoldiq: {current}, so'ralgan chiqim: {-qty}",
        )

    movement = StockMovement(
        tenant_id=tenant_id,
        store_id=store_id,
        product_id=product_id,
        qty=qty,
        kind=kind,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by=created_by,
    )
    session.add(movement)
    await session.flush()
    return movement


async def manual_movement(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    kind: str,
    qty: Decimal,
    note: str | None = None,
) -> StockMovement:
    """Tuzatish (adjustment, ishorali) yoki yo'qotish (writeoff, musbat kiritiladi, ishorasi serverda)."""
    await get_store(session, store_id)
    if kind == "writeoff":
        if qty <= 0:
            raise ProblemError(422, "Yo'qotish miqdori musbat bo'lishi kerak")
        signed = -qty
    elif kind == "adjustment":
        if qty == 0:
            raise ProblemError(422, "Tuzatish miqdori noldan farqli bo'lishi kerak")
        signed = qty
    else:
        raise ProblemError(422, "Noma'lum harakat turi")
    return await record_movement(
        session,
        tenant_id=tenant_id,
        store_id=store_id,
        product_id=product_id,
        qty=signed,
        kind=kind,
        created_by=user_id,
        note=note,
    )
