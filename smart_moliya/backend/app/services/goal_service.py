import uuid
from datetime import date
from decimal import Decimal

from app.models.goal import Goal
from app.repositories.goal_repository import GoalRepository
from app.schemas.goal import GoalCreate, GoalProgress
from app.services.exceptions import NotFoundError


class GoalService:
    def __init__(self, goal_repository: GoalRepository):
        self.goal_repository = goal_repository

    async def create_goal(self, user_id: uuid.UUID, data: GoalCreate) -> Goal:
        goal = Goal(
            user_id=user_id,
            title=data.title,
            target_amount=data.target_amount,
            current_amount=data.current_amount,
            target_date=data.target_date,
        )
        goal = await self.goal_repository.add(goal)
        await self.goal_repository.commit()
        return goal

    async def contribute(self, user_id: uuid.UUID, goal_id: uuid.UUID, amount: Decimal) -> Goal:
        goal = await self._get_owned(user_id, goal_id)
        goal.current_amount = Decimal(goal.current_amount) + amount
        await self.goal_repository.commit()
        return goal

    async def list_with_progress(self, user_id: uuid.UUID) -> list[GoalProgress]:
        goals = await self.goal_repository.list_by_user(user_id)
        today = date.today()
        results = []
        for goal in goals:
            target = Decimal(goal.target_amount)
            current = Decimal(goal.current_amount)
            progress_percent = float(min(100, (current / target * 100))) if target > 0 else 0.0
            results.append(
                GoalProgress(
                    id=goal.id,
                    title=goal.title,
                    target_amount=goal.target_amount,
                    current_amount=goal.current_amount,
                    target_date=goal.target_date,
                    monthly_required_saving=Decimal(str(goal.monthly_required_saving(today))),
                    progress_percent=round(progress_percent, 2),
                )
            )
        return results

    async def _get_owned(self, user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
        goal = await self.goal_repository.get(goal_id)
        if goal is None or goal.user_id != user_id:
            raise NotFoundError("Maqsad topilmadi")
        return goal
