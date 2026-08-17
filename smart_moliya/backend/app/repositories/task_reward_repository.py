import uuid

from sqlalchemy import select

from app.models.task_reward import TaskReward
from app.repositories.base import BaseRepository


class TaskRewardRepository(BaseRepository[TaskReward]):
    model = TaskReward

    async def list_for_family(self, family_group_id: uuid.UUID) -> list[TaskReward]:
        result = await self.session.execute(
            select(TaskReward).where(TaskReward.family_group_id == family_group_id)
        )
        return list(result.scalars().all())

    async def list_assigned_to(self, user_id: uuid.UUID) -> list[TaskReward]:
        result = await self.session.execute(
            select(TaskReward).where(TaskReward.assigned_to_user_id == user_id)
        )
        return list(result.scalars().all())
