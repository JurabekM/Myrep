import uuid
from datetime import date, timedelta

from app.models.achievement import Achievement
from app.models.user_progress import UserProgress
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.user_progress_repository import UserProgressRepository
from app.services.badges import BADGE_CATALOG


class GamificationService:
    def __init__(self, progress_repository: UserProgressRepository, achievement_repository: AchievementRepository):
        self.progress_repository = progress_repository
        self.achievement_repository = achievement_repository

    async def get_profile(self, user_id: uuid.UUID) -> UserProgress:
        return await self.progress_repository.get_or_create(user_id)

    async def add_xp(self, user_id: uuid.UUID, amount: int) -> UserProgress:
        progress = await self.progress_repository.get_or_create(user_id)
        progress.xp += amount
        progress.level = UserProgress.level_for_xp(progress.xp)
        await self.progress_repository.commit()
        return progress

    async def award_badge(self, user_id: uuid.UUID, badge_code: str) -> bool:
        """Badge'ni faqat birinchi marta beradi. True - yangi berildi, False - allaqachon bor."""
        if badge_code not in BADGE_CATALOG:
            raise ValueError(f"Noma'lum badge kodi: {badge_code}")

        already_has = await self.achievement_repository.has_badge(user_id, badge_code)
        if already_has:
            return False

        await self.achievement_repository.add(Achievement(user_id=user_id, badge_code=badge_code))
        xp_reward = BADGE_CATALOG[badge_code]["xp_reward"]
        await self.add_xp(user_id, xp_reward)
        await self.achievement_repository.commit()
        return True

    async def record_daily_activity(self, user_id: uuid.UUID) -> UserProgress:
        """Har kuni birinchi faoliyatda (masalan tranzaksiya qo'shilganda) chaqiriladi -
        streak'ni yangilaydi va tegishli badge'larni beradi."""
        progress = await self.progress_repository.get_or_create(user_id)
        today = date.today()

        if progress.last_activity_date == today:
            pass  # bugun allaqachon hisoblangan
        elif progress.last_activity_date == today - timedelta(days=1):
            progress.current_streak += 1
        else:
            progress.current_streak = 1

        progress.longest_streak = max(progress.longest_streak, progress.current_streak)
        progress.last_activity_date = today
        await self.progress_repository.commit()

        if progress.current_streak >= 7:
            await self.award_badge(user_id, "streak_7_days")
        if progress.current_streak >= 30:
            await self.award_badge(user_id, "streak_30_days")

        return progress

    async def leaderboard(self, limit: int = 10) -> list[UserProgress]:
        return await self.progress_repository.top_by_xp(limit)
