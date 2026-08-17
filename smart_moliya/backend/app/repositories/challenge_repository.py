from datetime import date

from sqlalchemy import select

from app.models.challenge import Challenge
from app.repositories.base import BaseRepository


class ChallengeRepository(BaseRepository[Challenge]):
    model = Challenge

    async def list_active(self) -> list[Challenge]:
        result = await self.session.execute(select(Challenge).where(Challenge.end_date >= date.today()))
        return list(result.scalars().all())
