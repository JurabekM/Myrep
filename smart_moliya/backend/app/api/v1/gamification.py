from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import (
    CurrentUser,
    get_achievement_repository,
    get_user_progress_repository,
)
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.user_progress_repository import UserProgressRepository
from app.schemas.gamification import BadgeInfo, LeaderboardEntry, ProgressRead
from app.services.badges import BADGE_CATALOG
from app.services.gamification_service import GamificationService

router = APIRouter(prefix="/gamification", tags=["gamification"])


def get_service(
    progress_repo: Annotated[UserProgressRepository, Depends(get_user_progress_repository)],
    achievement_repo: Annotated[AchievementRepository, Depends(get_achievement_repository)],
) -> GamificationService:
    return GamificationService(progress_repo, achievement_repo)


@router.get("/me", response_model=ProgressRead)
async def get_my_progress(current_user: CurrentUser, service: Annotated[GamificationService, Depends(get_service)]):
    progress = await service.get_profile(current_user.id)
    return ProgressRead.model_validate(progress)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(service: Annotated[GamificationService, Depends(get_service)]):
    top = await service.leaderboard()
    return [LeaderboardEntry(user_id=p.user_id, xp=p.xp, level=p.level) for p in top]


@router.get("/badges", response_model=list[BadgeInfo])
async def list_badge_catalog():
    return [BadgeInfo(code=code, **info) for code, info in BADGE_CATALOG.items()]
