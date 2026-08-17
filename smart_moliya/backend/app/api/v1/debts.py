import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_debt_repository
from app.repositories.debt_repository import DebtRepository
from app.schemas.debt import DebtCreate, DebtRead
from app.services.debt_service import DebtService

router = APIRouter(prefix="/debts", tags=["debts"])


def get_service(repo: Annotated[DebtRepository, Depends(get_debt_repository)]) -> DebtService:
    return DebtService(repo)


@router.get("", response_model=list[DebtRead])
async def list_debts(current_user: CurrentUser, service: Annotated[DebtService, Depends(get_service)]):
    debts = await service.list_debts(current_user.id)
    return [DebtRead.model_validate(d) for d in debts]


@router.post("", response_model=DebtRead, status_code=status.HTTP_201_CREATED)
async def create_debt(
    payload: DebtCreate, current_user: CurrentUser, service: Annotated[DebtService, Depends(get_service)]
):
    debt = await service.create_debt(current_user.id, payload)
    return DebtRead.model_validate(debt)


@router.post("/{debt_id}/settle", response_model=DebtRead)
async def settle_debt(
    debt_id: uuid.UUID, current_user: CurrentUser, service: Annotated[DebtService, Depends(get_service)]
):
    debt = await service.mark_settled(current_user.id, debt_id)
    return DebtRead.model_validate(debt)
