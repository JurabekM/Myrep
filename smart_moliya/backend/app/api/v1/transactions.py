import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentUser,
    get_achievement_repository,
    get_transaction_repository,
    get_user_progress_repository,
    get_wallet_repository,
)
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_progress_repository import UserProgressRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.transaction import TransactionCreate, TransactionRead
from app.services.gamification_service import GamificationService
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_service(
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    wallet_repo: Annotated[WalletRepository, Depends(get_wallet_repository)],
) -> TransactionService:
    return TransactionService(txn_repo, wallet_repo)


def get_gamification_service(
    progress_repo: Annotated[UserProgressRepository, Depends(get_user_progress_repository)],
    achievement_repo: Annotated[AchievementRepository, Depends(get_achievement_repository)],
) -> GamificationService:
    return GamificationService(progress_repo, achievement_repo)


@router.get("", response_model=list[TransactionRead])
async def list_transactions(
    current_user: CurrentUser, service: Annotated[TransactionService, Depends(get_service)]
):
    transactions = await service.list_transactions(current_user.id)
    return [TransactionRead.model_validate(t) for t in transactions]


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    current_user: CurrentUser,
    service: Annotated[TransactionService, Depends(get_service)],
    gamification_service: Annotated[GamificationService, Depends(get_gamification_service)],
):
    transaction = await service.create_transaction(current_user.id, payload)

    await gamification_service.record_daily_activity(current_user.id)
    await gamification_service.award_badge(current_user.id, "first_transaction")

    return TransactionRead.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[TransactionService, Depends(get_service)],
):
    await service.delete_transaction(current_user.id, transaction_id)
