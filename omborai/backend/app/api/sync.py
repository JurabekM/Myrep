"""Offline sinxronizatsiya.

Push: klient navbatidagi operatsiyalarni yuboradi. Har bir operatsiya o'z tranzaksiyasida bajariladi,
natija sync_ops jadvaliga yoziladi. Qayta yuborilsa, natija qayta hisoblanmaydi (idempotent).

Pull: keyset cursor (updated_at/created_at, id). Yaqinda o'zgargan (HORIZON soniyadan yangi) yozuvlar
hali qaytarilmaydi: parallel tranzaksiyalar commit tartibi buzilib, yozuv o'tkazib yuborilmasligi uchun.

Nizolar siyosati: tovarlar faqat serverda tahrirlanadi (klient yubormaydi), qoldiq va savdolar faqat
qo'shiladi. Shu sabab ziddiyat deyarli bo'lmaydi.
"""

import base64
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.catalog import to_product_out
from ..api.sales import to_sale_out
from ..db import get_db
from ..deps import Principal, get_principal
from ..errors import ProblemError
from ..models import Membership, Product, Sale, StockMovement, SyncOp
from ..schemas import (
    MovementOut,
    SyncMovementOp,
    SyncProductOut,
    SyncPullOut,
    SyncPushIn,
    SyncPushOut,
    SyncResultOut,
    SyncSaleOp,
)
from ..services.sales import SALE_ROLES, create_sale, find_sale
from ..services.stock import get_store, manual_movement

router = APIRouter(prefix="/sync", tags=["sync"])

HORIZON = timedelta(seconds=3)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
MOVEMENT_ROLES = ("owner", "manager", "warehouse")


def _encode_cursor(ts: datetime, row_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{ts.isoformat()}|{row_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    if not cursor:
        return EPOCH, uuid.UUID(int=0)
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_text, id_text = raw.split("|", 1)
        return datetime.fromisoformat(ts_text), uuid.UUID(id_text)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProblemError(422, "Cursor noto'g'ri") from exc


async def _apply_sale(session: AsyncSession, principal: Principal, op: SyncSaleOp) -> None:
    roles = set(
        (await session.execute(select(Membership.role).where(Membership.user_id == principal.user_id)))
        .scalars()
        .all()
    )
    if not roles & set(SALE_ROLES):
        raise ProblemError(403, "Ruxsat yo'q", "Savdo qilish uchun rolingiz yetarli emas")
    await get_store(session, op.payload.store_id)
    await create_sale(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        roles=roles,
        body=op.payload,
    )


async def _apply_movement(session: AsyncSession, principal: Principal, op: SyncMovementOp) -> None:
    roles = set(
        (await session.execute(select(Membership.role).where(Membership.user_id == principal.user_id)))
        .scalars()
        .all()
    )
    if not roles & set(MOVEMENT_ROLES):
        raise ProblemError(403, "Ruxsat yo'q", "Qoldiq o'zgartirish uchun rolingiz yetarli emas")
    await manual_movement(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        store_id=op.payload.store_id,
        product_id=op.payload.product_id,
        kind=op.payload.kind,
        qty=op.payload.qty,
        note=op.payload.note,
    )


async def _process(
    session: AsyncSession, principal: Principal, op: SyncSaleOp | SyncMovementOp
) -> SyncResultOut:
    existing = await session.get(SyncOp, op.op_id)
    if existing is not None:
        return SyncResultOut(
            op_id=op.op_id,
            status="applied" if existing.status == "applied" else "rejected",
            duplicate=True,
            error_title=existing.error_title,
            error_detail=existing.error_detail,
        )

    if op.type == "sale" and await find_sale(session, op.op_id) is not None:
        # Savdo boshqa yo'l bilan (to'g'ridan-to'g'ri API orqali) allaqachon yaratilgan
        session.add(SyncOp(op_id=op.op_id, tenant_id=principal.tenant_id, op_type=op.type, status="applied"))
        await session.commit()
        return SyncResultOut(op_id=op.op_id, status="applied", duplicate=True)

    try:
        if op.type == "sale":
            await _apply_sale(session, principal, op)
        else:
            await _apply_movement(session, principal, op)
        session.add(SyncOp(op_id=op.op_id, tenant_id=principal.tenant_id, op_type=op.type, status="applied"))
        await session.commit()
        return SyncResultOut(op_id=op.op_id, status="applied")
    except ProblemError as exc:
        await session.rollback()  # operatsiyaning hech bir qismi saqlanmaydi
        detail = str(exc.detail)[:500] if exc.detail else None
        session.add(
            SyncOp(
                op_id=op.op_id,
                tenant_id=principal.tenant_id,
                op_type=op.type,
                status="rejected",
                error_title=exc.title[:200],
                error_detail=detail,
            )
        )
        await session.commit()
        return SyncResultOut(op_id=op.op_id, status="rejected", error_title=exc.title, error_detail=detail)
    except IntegrityError:
        # Bir vaqtda bir xil operatsiya kelgan: natijani o'qiymiz
        await session.rollback()
        prior = await session.get(SyncOp, op.op_id)
        if prior is not None:
            return SyncResultOut(
                op_id=op.op_id,
                status="applied" if prior.status == "applied" else "rejected",
                duplicate=True,
            )
        raise


@router.post("/push", response_model=SyncPushOut)
async def push(
    body: SyncPushIn,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> SyncPushOut:
    results = [await _process(session, principal, op) for op in body.ops]
    return SyncPushOut(results=results)


@router.get("/pull", response_model=SyncPullOut)
async def pull(
    store_id: uuid.UUID,
    products_cursor: str = "",
    movements_cursor: str = "",
    sales_cursor: str = "",
    limit: int = Query(default=200, ge=1, le=500),
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> SyncPullOut:
    horizon = datetime.now(UTC) - HORIZON
    await get_store(session, store_id)

    # Tovarlar (tenant bo'yicha, o'chirilganlari ham — klient keshidan olib tashlashi uchun)
    p_ts, p_id = _decode_cursor(products_cursor)
    rows = (
        (
            await session.execute(
                select(Product)
                .where(
                    Product.updated_at < horizon,
                    or_(
                        Product.updated_at > p_ts,
                        and_(Product.updated_at == p_ts, Product.id > p_id),
                    ),
                )
                .order_by(Product.updated_at, Product.id)
                .limit(limit + 1)
            )
        )
        .scalars()
        .all()
    )
    p_more = len(rows) > limit
    p_page = rows[:limit]
    p_out = await to_product_out(session, list(p_page), None)
    products = [
        SyncProductOut(**out.model_dump(exclude={"stock_qty"}), deleted=p.deleted_at is not None)
        for out, p in zip(p_out, p_page, strict=True)
    ]
    p_cursor = _encode_cursor(p_page[-1].updated_at, p_page[-1].id) if p_page else products_cursor

    # Qoldiq harakatlari (append-only ledger)
    m_ts, m_id = _decode_cursor(movements_cursor)
    m_rows = (
        (
            await session.execute(
                select(StockMovement)
                .where(
                    StockMovement.store_id == store_id,
                    StockMovement.created_at < horizon,
                    or_(
                        StockMovement.created_at > m_ts,
                        and_(StockMovement.created_at == m_ts, StockMovement.id > m_id),
                    ),
                )
                .order_by(StockMovement.created_at, StockMovement.id)
                .limit(limit + 1)
            )
        )
        .scalars()
        .all()
    )
    m_more = len(m_rows) > limit
    m_page = m_rows[:limit]
    m_cursor = _encode_cursor(m_page[-1].created_at, m_page[-1].id) if m_page else movements_cursor
    movements = [MovementOut.model_validate(m, from_attributes=True) for m in m_page]

    # Cheklar (status o'zgarishi — qaytarish — ham qayta yuboriladi)
    s_ts, s_id = _decode_cursor(sales_cursor)
    s_rows = (
        (
            await session.execute(
                select(Sale)
                .where(
                    Sale.store_id == store_id,
                    Sale.updated_at < horizon,
                    or_(Sale.updated_at > s_ts, and_(Sale.updated_at == s_ts, Sale.id > s_id)),
                )
                .order_by(Sale.updated_at, Sale.id)
                .limit(limit + 1)
            )
        )
        .scalars()
        .all()
    )
    s_more = len(s_rows) > limit
    s_page = s_rows[:limit]
    s_cursor = _encode_cursor(s_page[-1].updated_at, s_page[-1].id) if s_page else sales_cursor
    sales = [await to_sale_out(session, s) for s in s_page]

    return SyncPullOut(
        products=products,
        movements=movements,
        sales=sales,
        cursors={"products": p_cursor, "movements": m_cursor, "sales": s_cursor},
        has_more=p_more or m_more or s_more,
    )
