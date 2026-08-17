import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_wallet_repository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.wallet import WalletCreate, WalletRead, WalletUpdate
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallets", tags=["wallets"])


def get_service(repo: Annotated[WalletRepository, Depends(get_wallet_repository)]) -> WalletService:
    return WalletService(repo)


@router.get("", response_model=list[WalletRead])
async def list_wallets(current_user: CurrentUser, service: Annotated[WalletService, Depends(get_service)]):
    wallets = await service.list_wallets(current_user.id)
    return [WalletRead.model_validate(w) for w in wallets]


@router.post("", response_model=WalletRead, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    payload: WalletCreate, current_user: CurrentUser, service: Annotated[WalletService, Depends(get_service)]
):
    wallet = await service.create_wallet(current_user.id, payload)
    return WalletRead.model_validate(wallet)


@router.patch("/{wallet_id}", response_model=WalletRead)
async def update_wallet(
    wallet_id: uuid.UUID,
    payload: WalletUpdate,
    current_user: CurrentUser,
    service: Annotated[WalletService, Depends(get_service)],
):
    wallet = await service.update_wallet(current_user.id, wallet_id, payload)
    return WalletRead.model_validate(wallet)


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wallet(
    wallet_id: uuid.UUID, current_user: CurrentUser, service: Annotated[WalletService, Depends(get_service)]
):
    await service.delete_wallet(current_user.id, wallet_id)
