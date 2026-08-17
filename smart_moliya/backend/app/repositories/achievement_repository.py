import uuid

from sqlalchemy import select

from app.models.achievement import Achievement
from app.repositories.base import BaseRepository


class AchievementRepository(BaseRepository[Achievement]):
    model = Achievement

    async def has_badge(self, user_id: uuid.UUID, badge_code: str) -> bool:
        result = await self.session.execute(
            select(Achievement).where(Achievement.user_id == user_id, Achievement.badge_code == badge_code)
        )
        return result.scalar_one_or_none() is not None
