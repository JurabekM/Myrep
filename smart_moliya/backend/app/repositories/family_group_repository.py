import uuid

from sqlalchemy import select

from app.models.family_group import FamilyGroup
from app.models.user import User
from app.repositories.base import BaseRepository


class FamilyGroupRepository(BaseRepository[FamilyGroup]):
    model = FamilyGroup

    async def list_members(self, family_group_id: uuid.UUID) -> list[User]:
        result = await self.session.execute(select(User).where(User.family_group_id == family_group_id))
        return list(result.scalars().all())
