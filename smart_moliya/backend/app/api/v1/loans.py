from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_loan_repository
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import LoanCreate, LoanRead, LoanStatus
from app.services.loan_service import LoanService

router = APIRouter(prefix="/loans", tags=["loans"])


def get_service(repo: Annotated[LoanRepository, Depends(get_loan_repository)]) -> LoanService:
    return LoanService(repo)


@router.get("", response_model=list[LoanStatus])
async def list_loans(current_user: CurrentUser, service: Annotated[LoanService, Depends(get_service)]):
    return await service.list_with_status(current_user.id)


@router.post("", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
async def create_loan(
    payload: LoanCreate, current_user: CurrentUser, service: Annotated[LoanService, Depends(get_service)]
):
    loan = await service.create_loan(current_user.id, payload)
    return LoanRead.model_validate(loan)
