import uuid

from sqlalchemy import select

from app.models.user_progress import UserProgress
from app.repositories.base import BaseRepository


class UserProgressRepository(BaseRepository[UserProgress]):
    model = UserProgress

    async def get_or_create(self, user_id: uuid.UUID) -> UserProgress:
        progress = await self.session.get(UserProgress, user_id)
        if progress is None:
            # Qiymatlar aniq beriladi - `mapped_column(default=...)` faqat flush/INSERT
            # vaqtida qo'llanadi, shu obyekt hali flush qilinmagan holatda ishlatilishi mumkin.
            progress = UserProgress(
                user_id=user_id, xp=0, level=1, current_streak=0, longest_streak=0
            )
            progress = await self.add(progress)
        return progress

    async def top_by_xp(self, limit: int = 10) -> list[UserProgress]:
        result = await self.session.execute(
            select(UserProgress).order_by(UserProgress.xp.desc()).limit(limit)
        )
        return list(result.scalars().all())
