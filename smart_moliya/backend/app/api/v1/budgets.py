from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentUser,
    get_achievement_repository,
    get_budget_repository,
    get_transaction_repository,
    get_user_progress_repository,
)
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_progress_repository import UserProgressRepository
from app.schemas.budget import BudgetCreate, BudgetRead, BudgetStatus
from app.services.budget_service import BudgetService
from app.services.gamification_service import GamificationService

router = APIRouter(prefix="/budgets", tags=["budgets"])


def get_service(
    budget_repo: Annotated[BudgetRepository, Depends(get_budget_repository)],
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> BudgetService:
    return BudgetService(budget_repo, txn_repo)


def get_gamification_service(
    progress_repo: Annotated[UserProgressRepository, Depends(get_user_progress_repository)],
    achievement_repo: Annotated[AchievementRepository, Depends(get_achievement_repository)],
) -> GamificationService:
    return GamificationService(progress_repo, achievement_repo)


@router.get("", response_model=list[BudgetStatus])
async def list_budgets(current_user: CurrentUser, service: Annotated[BudgetService, Depends(get_service)]):
    return await service.list_with_status(current_user.id)


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    current_user: CurrentUser,
    service: Annotated[BudgetService, Depends(get_service)],
    gamification_service: Annotated[GamificationService, Depends(get_gamification_service)],
):
    budget = await service.create_budget(current_user.id, payload)
    await gamification_service.award_badge(current_user.id, "first_budget_created")
    return BudgetRead.model_validate(budget)
