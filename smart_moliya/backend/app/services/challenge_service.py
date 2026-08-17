import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

from app.models.challenge import Challenge, UserChallenge
from app.models.enums import ChallengeTargetType, TransactionType
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_challenge_repository import UserChallengeRepository
from app.services.exceptions import ConflictError, NotFoundError
from app.services.gamification_service import GamificationService


class ChallengeService:
    def __init__(
        self,
        challenge_repository: ChallengeRepository,
        user_challenge_repository: UserChallengeRepository,
        transaction_repository: TransactionRepository,
        gamification_service: GamificationService,
    ):
        self.challenge_repository = challenge_repository
        self.user_challenge_repository = user_challenge_repository
        self.transaction_repository = transaction_repository
        self.gamification_service = gamification_service

    async def list_active_challenges(self) -> list[Challenge]:
        return await self.challenge_repository.list_active()

    async def join(self, user_id: uuid.UUID, challenge_id: uuid.UUID) -> UserChallenge:
        challenge = await self.challenge_repository.get(challenge_id)
        if challenge is None:
            raise NotFoundError("Challenge topilmadi")

        existing = await self.user_challenge_repository.get_for_user_and_challenge(user_id, challenge_id)
        if existing is not None:
            raise ConflictError("Siz bu challenge'ga allaqachon qo'shilgansiz")

        user_challenge = UserChallenge(user_id=user_id, challenge_id=challenge_id)
        user_challenge = await self.user_challenge_repository.add(user_challenge)
        await self.user_challenge_repository.commit()
        return user_challenge

    async def list_my_challenges(self, user_id: uuid.UUID) -> list[UserChallenge]:
        return await self.user_challenge_repository.list_for_user(user_id)

    async def evaluate_progress(self, user_id: uuid.UUID, challenge_id: uuid.UUID) -> UserChallenge:
        """Foydalanuvchining haqiqiy tranzaksiyalari asosida progressni qayta hisoblaydi
        va target'ga yetgan bo'lsa yakunlaydi (XP + badge beriladi)."""
        user_challenge = await self.user_challenge_repository.get_for_user_and_challenge(user_id, challenge_id)
        if user_challenge is None:
            raise NotFoundError("Siz bu challenge'ga qo'shilmagansiz")

        challenge = await self.challenge_repository.get(challenge_id)
        if challenge is None:
            raise NotFoundError("Challenge topilmadi")

        start = datetime.combine(challenge.start_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(challenge.end_date, time.max, tzinfo=timezone.utc)
        transactions = await self.transaction_repository.list_between(user_id, start, end)

        if challenge.target_type == ChallengeTargetType.SAVE_AMOUNT:
            income = sum(Decimal(t.amount) for t in transactions if t.type == TransactionType.INCOME)
            expense = sum(Decimal(t.amount) for t in transactions if t.type == TransactionType.EXPENSE)
            progress_value = income - expense
        else:  # NO_SPEND_DAYS
            spend_days = {t.occurred_at.date() for t in transactions if t.type == TransactionType.EXPENSE}
            total_days = (challenge.end_date - challenge.start_date).days + 1
            progress_value = Decimal(total_days - len(spend_days))

        user_challenge.progress_value = progress_value
        is_completed = progress_value >= Decimal(challenge.target_value)

        if is_completed and user_challenge.completed_at is None:
            user_challenge.completed_at = datetime.now(timezone.utc)
            await self.gamification_service.add_xp(user_id, challenge.xp_reward)
            await self.gamification_service.award_badge(user_id, "challenge_completed")

        await self.user_challenge_repository.commit()
        return user_challenge
