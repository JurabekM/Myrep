import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import Principal, get_principal, require_roles
from ..errors import ProblemError
from ..models import Shift
from ..schemas import ShiftCloseIn, ShiftOpenIn, ShiftOut, ShiftSummaryOut
from ..services.sales import SALE_ROLES, open_shift_for_store, shift_summary
from ..services.stock import get_store

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.post("", status_code=201, response_model=ShiftOut)
async def open_shift(
    body: ShiftOpenIn,
    principal: Principal = Depends(require_roles(*SALE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> Shift:
    await get_store(session, body.store_id)
    shift = Shift(
        tenant_id=principal.tenant_id,
        store_id=body.store_id,
        opened_by=principal.user_id,
        opening_cash=body.opening_cash,
    )
    session.add(shift)
    try:
        await session.commit()
    except IntegrityError as exc:  # partial unique index: bir do'konda bitta ochiq smena
        raise ProblemError(409, "Smena allaqachon ochiq") from exc
    return shift


@router.get("/current", response_model=ShiftOut)
async def current_shift(
    store_id: uuid.UUID,
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> Shift:
    return await open_shift_for_store(session, store_id)


@router.post("/{shift_id}/close", response_model=ShiftSummaryOut)
async def close_shift(
    shift_id: uuid.UUID,
    body: ShiftCloseIn,
    principal: Principal = Depends(require_roles(*SALE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> ShiftSummaryOut:
    shift = await session.scalar(select(Shift).where(Shift.id == shift_id).with_for_update())
    if shift is None:
        raise ProblemError(404, "Smena topilmadi")
    if shift.closed_at is not None:
        raise ProblemError(409, "Smena allaqachon yopilgan")

    shift.closed_at = datetime.now(UTC)
    shift.closed_by = principal.user_id
    shift.closing_cash = body.closing_cash
    shift.version += 1

    summary = await shift_summary(session, shift)
    await session.commit()

    expected = summary["expected_cash"]
    return ShiftSummaryOut(
        shift=ShiftOut.model_validate(shift, from_attributes=True),
        closing_cash=body.closing_cash,
        difference=body.closing_cash - expected,
        **summary,
    )
