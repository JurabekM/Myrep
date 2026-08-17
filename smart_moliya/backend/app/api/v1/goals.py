import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentUser,
    get_achievement_repository,
    get_goal_repository,
    get_user_progress_repository,
)
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.user_progress_repository import UserProgressRepository
from app.schemas.goal import GoalContribution, GoalCreate, GoalProgress, GoalRead
from app.services.gamification_service import GamificationService
from app.services.goal_service import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


def get_service(repo: Annotated[GoalRepository, Depends(get_goal_repository)]) -> GoalService:
    return GoalService(repo)


def get_gamification_service(
    progress_repo: Annotated[UserProgressRepository, Depends(get_user_progress_repository)],
    achievement_repo: Annotated[AchievementRepository, Depends(get_achievement_repository)],
) -> GamificationService:
    return GamificationService(progress_repo, achievement_repo)


@router.get("", response_model=list[GoalProgress])
async def list_goals(current_user: CurrentUser, service: Annotated[GoalService, Depends(get_service)]):
    return await service.list_with_progress(current_user.id)


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate, current_user: CurrentUser, service: Annotated[GoalService, Depends(get_service)]
):
    goal = await service.create_goal(current_user.id, payload)
    return GoalRead.model_validate(goal)


@router.post("/{goal_id}/contribute", response_model=GoalRead)
async def contribute(
    goal_id: uuid.UUID,
    payload: GoalContribution,
    current_user: CurrentUser,
    service: Annotated[GoalService, Depends(get_service)],
    gamification_service: Annotated[GamificationService, Depends(get_gamification_service)],
):
    goal = await service.contribute(current_user.id, goal_id, payload.amount)

    if Decimal(goal.current_amount) >= Decimal(goal.target_amount):
        await gamification_service.award_badge(current_user.id, "first_goal_completed")

    return GoalRead.model_validate(goal)
