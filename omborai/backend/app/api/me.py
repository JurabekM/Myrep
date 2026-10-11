from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import Principal, get_principal
from ..errors import ProblemError
from ..models import Membership, User
from ..schemas import MembershipOut, MeOut

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut)
async def me(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> MeOut:
    user = await session.scalar(select(User).where(User.id == principal.user_id, User.deleted_at.is_(None)))
    if user is None:
        raise ProblemError(401, "Foydalanuvchi topilmadi")
    rows = await session.execute(
        select(Membership.store_id, Membership.role).where(Membership.user_id == user.id)
    )
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=principal.tenant_id,
        memberships=[MembershipOut(store_id=s, role=r) for s, r in rows.all()],
    )
