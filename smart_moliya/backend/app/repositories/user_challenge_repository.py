import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.challenge import UserChallenge
from app.repositories.base import BaseRepository


class UserChallengeRepository(BaseRepository[UserChallenge]):
    model = UserChallenge

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserChallenge]:
        result = await self.session.execute(
            select(UserChallenge)
            .where(UserChallenge.user_id == user_id)
            .options(selectinload(UserChallenge.challenge))
        )
        return list(result.scalars().all())

    async def get_for_user_and_challenge(
        self, user_id: uuid.UUID, challenge_id: uuid.UUID
    ) -> UserChallenge | None:
        result = await self.session.execute(
            select(UserChallenge).where(
                UserChallenge.user_id == user_id, UserChallenge.challenge_id == challenge_id
            )
        )
        return result.scalar_one_or_none()
