from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_transaction_repository, get_wallet_repository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.sync import SyncPullResponse, SyncPushRequest, SyncPushResponse
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


def get_service(
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    wallet_repo: Annotated[WalletRepository, Depends(get_wallet_repository)],
) -> SyncService:
    return SyncService(txn_repo, wallet_repo)


@router.post("/push", response_model=SyncPushResponse)
async def push(
    payload: SyncPushRequest, current_user: CurrentUser, service: Annotated[SyncService, Depends(get_service)]
):
    accepted = await service.push(current_user.id, payload)
    return SyncPushResponse(accepted=accepted)


@router.get("/pull", response_model=SyncPullResponse)
async def pull(
    current_user: CurrentUser,
    service: Annotated[SyncService, Depends(get_service)],
    since_version: int = 0,
):
    return await service.pull(current_user.id, since_version)
