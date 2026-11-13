from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import Principal, get_principal, require_roles
from ..models import Store
from ..schemas import StoreIn, StoreOut

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreOut])
async def list_stores(
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> list[Store]:
    # Tenant filtri RLS orqali avtomatik qo'llanadi
    result = await session.execute(select(Store).where(Store.deleted_at.is_(None)).order_by(Store.created_at))
    return list(result.scalars().all())


@router.post("", status_code=201, response_model=StoreOut)
async def create_store(
    body: StoreIn,
    principal: Principal = Depends(require_roles("owner", "manager")),
    session: AsyncSession = Depends(get_db),
) -> Store:
    store = Store(tenant_id=principal.tenant_id, name=body.name)
    session.add(store)
    await session.commit()
    return store
