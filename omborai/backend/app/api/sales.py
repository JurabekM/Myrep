import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, set_db_context
from ..deps import Principal, get_principal, require_roles
from ..errors import ProblemError
from ..models import Membership, Payment, Sale, SaleItem
from ..schemas import PaymentOut, SaleIn, SaleItemOut, SaleOut
from ..services.sales import REFUND_ROLES, SALE_ROLES, create_sale, find_sale, refund_sale
from ..services.stock import get_store

router = APIRouter(prefix="/sales", tags=["sales"])


async def to_sale_out(session: AsyncSession, sale: Sale) -> SaleOut:
    items = (await session.execute(select(SaleItem).where(SaleItem.sale_id == sale.id))).scalars().all()
    payments = (await session.execute(select(Payment).where(Payment.sale_id == sale.id))).scalars().all()
    return SaleOut(
        id=sale.id,
        number=sale.number,
        store_id=sale.store_id,
        shift_id=sale.shift_id,
        status=sale.status,
        subtotal=sale.subtotal,
        discount=sale.discount,
        total=sale.total,
        created_by=sale.created_by,
        created_at=sale.created_at,
        client_created_at=sale.client_created_at,
        items=[
            SaleItemOut(
                product_id=i.product_id,
                product_name=i.product_name,
                unit=i.unit,
                qty=i.qty,
                unit_price=i.unit_price,
                line_total=i.line_total,
            )
            for i in items
        ],
        payments=[PaymentOut(method=p.method, amount=p.amount) for p in payments],
    )


@router.post("", response_model=SaleOut, responses={201: {"description": "Yangi chek yaratildi"}})
async def create_sale_endpoint(
    body: SaleIn,
    response: Response,
    principal: Principal = Depends(require_roles(*SALE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> SaleOut:
    """Idempotent: bir xil id qayta yuborilsa, 200 bilan mavjud chek qaytadi (yangi chek yaratilmaydi)."""
    existing = await find_sale(session, body.id)
    if existing is not None:
        response.status_code = 200
        return await to_sale_out(session, existing)

    await get_store(session, body.store_id)
    roles = set(
        (await session.execute(select(Membership.role).where(Membership.user_id == principal.user_id)))
        .scalars()
        .all()
    )
    try:
        sale = await create_sale(
            session,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            roles=roles,
            body=body,
        )
        await session.commit()
    except IntegrityError as exc:
        # Bir vaqtda bir xil id bilan ikkinchi so'rov kelgan: mavjud chekni qaytaramiz
        await session.rollback()
        await set_db_context(session, tenant_id=principal.tenant_id, user_id=None)
        existing = await find_sale(session, body.id)
        if existing is None:
            raise ProblemError(409, "Savdo to'qnashuvi") from exc
        response.status_code = 200
        return await to_sale_out(session, existing)

    response.status_code = 201
    return await to_sale_out(session, sale)


@router.get("", response_model=list[SaleOut])
async def list_sales(
    store_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> list[SaleOut]:
    rows = await session.execute(
        select(Sale).where(Sale.store_id == store_id).order_by(Sale.created_at.desc()).limit(limit)
    )
    return [await to_sale_out(session, s) for s in rows.scalars().all()]


@router.get("/{sale_id}", response_model=SaleOut)
async def get_sale(
    sale_id: uuid.UUID,
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> SaleOut:
    sale = await find_sale(session, sale_id)
    if sale is None:
        raise ProblemError(404, "Chek topilmadi")
    return await to_sale_out(session, sale)


@router.post("/{sale_id}/refund", response_model=SaleOut)
async def refund(
    sale_id: uuid.UUID,
    principal: Principal = Depends(require_roles(*REFUND_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> SaleOut:
    sale = await refund_sale(
        session, sale_id=sale_id, user_id=principal.user_id, tenant_id=principal.tenant_id
    )
    await session.commit()
    return await to_sale_out(session, sale)
