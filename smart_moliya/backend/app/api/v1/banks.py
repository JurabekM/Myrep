import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_transaction_repository, get_wallet_repository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.bank import BankAccount, BankInfo, BankSyncResult
from app.services.bank_service import BankService

router = APIRouter(prefix="/banks", tags=["banks"])


def get_service(
    wallet_repo: Annotated[WalletRepository, Depends(get_wallet_repository)],
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> BankService:
    return BankService(wallet_repo, txn_repo)


@router.get("", response_model=list[BankInfo])
async def list_banks(service: Annotated[BankService, Depends(get_service)]):
    return service.list_banks()


@router.post("/{bank_code}/link", response_model=BankAccount)
async def link_bank_account(
    bank_code: str, current_user: CurrentUser, service: Annotated[BankService, Depends(get_service)]
):
    return await service.link_account(bank_code, current_user.id)


@router.post("/{bank_code}/sync", response_model=BankSyncResult)
async def sync_bank_transactions(
    bank_code: str,
    wallet_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[BankService, Depends(get_service)],
):
    return await service.sync_transactions(bank_code, current_user.id, wallet_id)
