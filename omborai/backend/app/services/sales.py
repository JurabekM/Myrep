"""Savdo (chek), to'lov, qaytarish va smena hisobi.

Qoidalar:
- Narxlar faqat serverda (products.sale_price) olinadi; klient narx yubora olmaydi.
- Tovarlar id bo'yicha tartiblab qulflanadi (deadlock'ning oldini olish uchun).
- Savdo id'si klientda yaratiladi: qayta yuborilsa, yangi chek emas, mavjud chek qaytadi.
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ProblemError
from ..models import Payment, Sale, SaleItem, Shift
from ..schemas import SaleIn
from .stock import lock_product, record_movement

SALE_ROLES = ("owner", "manager", "cashier")
DISCOUNT_ROLES = ("owner", "manager")
REFUND_ROLES = ("owner", "manager")


def _money(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


async def open_shift_for_store(session: AsyncSession, store_id: uuid.UUID) -> Shift:
    shift = await session.scalar(select(Shift).where(Shift.store_id == store_id, Shift.closed_at.is_(None)))
    if shift is None:
        raise ProblemError(409, "Smena ochilmagan", "Avval kassa smenasini oching")
    return shift


async def find_sale(session: AsyncSession, sale_id: uuid.UUID) -> Sale | None:
    return await session.scalar(select(Sale).where(Sale.id == sale_id))


async def create_sale(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    roles: set[str],
    body: SaleIn,
) -> Sale:
    shift = await open_shift_for_store(session, body.store_id)

    if body.discount > 0 and not roles & set(DISCOUNT_ROLES):
        raise ProblemError(403, "Ruxsat yo'q", "Chegirma faqat egasi yoki menejer tomonidan beriladi")

    # Qulflash tartibi: product id bo'yicha
    lines = sorted(body.items, key=lambda line: line.product_id)
    products = {}
    for line in lines:
        product = await lock_product(session, line.product_id)
        if not product.is_active:
            raise ProblemError(422, "Tovar faol emas", product.name)
        products[line.product_id] = product

    sale_items: list[SaleItem] = []
    subtotal = 0
    for line in body.items:
        product = products[line.product_id]
        line_total = _money(line.qty * product.sale_price)
        subtotal += line_total
        sale_items.append(
            SaleItem(
                tenant_id=tenant_id,
                product_id=product.id,
                product_name=product.name,
                unit=product.unit,
                qty=line.qty,
                unit_price=product.sale_price,
                line_total=line_total,
            )
        )

    if body.discount > subtotal:
        raise ProblemError(422, "Chegirma jami summadan katta bo'lishi mumkin emas")
    total = subtotal - body.discount
    if total <= 0:
        raise ProblemError(422, "To'lov summasi noldan katta bo'lishi kerak")
    paid = sum(p.amount for p in body.payments)
    if paid != total:
        raise ProblemError(422, "To'lov summasi mos emas", f"Jami: {total}, to'landi: {paid}")

    sale = Sale(
        id=body.id,
        tenant_id=tenant_id,
        store_id=body.store_id,
        shift_id=shift.id,
        status="completed",
        subtotal=subtotal,
        discount=body.discount,
        total=total,
        created_by=user_id,
        client_created_at=body.client_created_at,
    )
    session.add(sale)
    await session.flush()  # takroriy id bu yerda IntegrityError beradi, qoldiq hali o'zgarmagan
    await session.refresh(sale, attribute_names=["number", "created_at"])

    for item in sale_items:
        item.sale_id = sale.id
        session.add(item)
    for payment in body.payments:
        session.add(
            Payment(tenant_id=tenant_id, sale_id=sale.id, method=payment.method, amount=payment.amount)
        )
    await session.flush()

    for item in sale_items:
        await record_movement(
            session,
            tenant_id=tenant_id,
            store_id=body.store_id,
            product_id=item.product_id,
            qty=-item.qty,
            kind="sale",
            created_by=user_id,
            reference_type="sale",
            reference_id=sale.id,
        )
    return sale


async def refund_sale(
    session: AsyncSession, *, sale_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID
) -> Sale:
    # Chekni qulflaymiz: bir vaqtda ikki marta qaytarib bo'lmaydi
    sale = await session.scalar(select(Sale).where(Sale.id == sale_id).with_for_update())
    if sale is None:
        raise ProblemError(404, "Chek topilmadi")
    if sale.status == "refunded":
        raise ProblemError(409, "Chek allaqachon qaytarilgan")

    items = (
        (
            await session.execute(
                select(SaleItem).where(SaleItem.sale_id == sale.id).order_by(SaleItem.product_id)
            )
        )
        .scalars()
        .all()
    )
    for item in items:
        await record_movement(
            session,
            tenant_id=tenant_id,
            store_id=sale.store_id,
            product_id=item.product_id,
            qty=item.qty,
            kind="sale_return",
            created_by=user_id,
            reference_type="sale",
            reference_id=sale.id,
        )
    sale.status = "refunded"
    sale.updated_at = func.now()
    await session.flush()
    return sale


async def shift_summary(session: AsyncSession, shift: Shift) -> dict:
    sales_rows = await session.execute(
        select(Sale.status, func.count(), func.coalesce(func.sum(Sale.total), 0))
        .where(Sale.shift_id == shift.id)
        .group_by(Sale.status)
    )
    counts = {status: (int(n), int(total)) for status, n, total in sales_rows.all()}

    pay_rows = await session.execute(
        select(Sale.status, Payment.method, func.coalesce(func.sum(Payment.amount), 0))
        .join(Sale, Sale.id == Payment.sale_id)
        .where(Sale.shift_id == shift.id)
        .group_by(Sale.status, Payment.method)
    )
    by_method: dict[str, int] = {}
    cash_refunds = 0
    for status, method, amount in pay_rows.all():
        if status == "completed":
            by_method[method] = by_method.get(method, 0) + int(amount)
        elif method == "cash":
            cash_refunds += int(amount)

    sales_count, total_sales = counts.get("completed", (0, 0))
    refunds_count, total_refunds = counts.get("refunded", (0, 0))
    cash_sales = by_method.get("cash", 0)
    expected_cash = shift.opening_cash + cash_sales - cash_refunds
    return {
        "sales_count": sales_count,
        "total_sales": total_sales,
        "refunds_count": refunds_count,
        "total_refunds": total_refunds,
        "by_method": by_method,
        "expected_cash": expected_cash,
    }
