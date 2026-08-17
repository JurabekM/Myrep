import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentUser,
    get_achievement_repository,
    get_challenge_repository,
    get_transaction_repository,
    get_user_challenge_repository,
    get_user_progress_repository,
)
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_challenge_repository import UserChallengeRepository
from app.repositories.user_progress_repository import UserProgressRepository
from app.schemas.challenge import ChallengeRead, UserChallengeRead
from app.services.challenge_service import ChallengeService
from app.services.gamification_service import GamificationService

router = APIRouter(prefix="/challenges", tags=["challenges"])


def get_service(
    challenge_repo: Annotated[ChallengeRepository, Depends(get_challenge_repository)],
    user_challenge_repo: Annotated[UserChallengeRepository, Depends(get_user_challenge_repository)],
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    progress_repo: Annotated[UserProgressRepository, Depends(get_user_progress_repository)],
    achievement_repo: Annotated[AchievementRepository, Depends(get_achievement_repository)],
) -> ChallengeService:
    gamification_service = GamificationService(progress_repo, achievement_repo)
    return ChallengeService(challenge_repo, user_challenge_repo, txn_repo, gamification_service)


@router.get("", response_model=list[ChallengeRead])
async def list_active_challenges(service: Annotated[ChallengeService, Depends(get_service)]):
    challenges = await service.list_active_challenges()
    return [ChallengeRead.model_validate(c) for c in challenges]


@router.post("/{challenge_id}/join", response_model=UserChallengeRead, status_code=status.HTTP_201_CREATED)
async def join_challenge(
    challenge_id: uuid.UUID, current_user: CurrentUser, service: Annotated[ChallengeService, Depends(get_service)]
):
    user_challenge = await service.join(current_user.id, challenge_id)
    await service.evaluate_progress(current_user.id, challenge_id)
    refreshed = await service.user_challenge_repository.get_for_user_and_challenge(current_user.id, challenge_id)
    return UserChallengeRead.model_validate(refreshed or user_challenge)


@router.get("/mine", response_model=list[UserChallengeRead])
async def list_my_challenges(current_user: CurrentUser, service: Annotated[ChallengeService, Depends(get_service)]):
    user_challenges = await service.list_my_challenges(current_user.id)
    return [UserChallengeRead.model_validate(uc) for uc in user_challenges]


@router.post("/{challenge_id}/refresh", response_model=UserChallengeRead)
async def refresh_challenge_progress(
    challenge_id: uuid.UUID, current_user: CurrentUser, service: Annotated[ChallengeService, Depends(get_service)]
):
    user_challenge = await service.evaluate_progress(current_user.id, challenge_id)
    return UserChallengeRead.model_validate(user_challenge)
