import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.models.enums import TaskRewardStatus, TransactionSource, TransactionType
from app.models.family_group import FamilyGroup
from app.models.task_reward import TaskReward
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.family_group_repository import FamilyGroupRepository
from app.repositories.task_reward_repository import TaskRewardRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.wallet_repository import WalletRepository
from app.services.exceptions import ConflictError, NotFoundError, UnauthorizedError


class FamilyService:
    def __init__(
        self,
        family_group_repository: FamilyGroupRepository,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        transaction_repository: TransactionRepository,
        task_reward_repository: TaskRewardRepository,
    ):
        self.family_group_repository = family_group_repository
        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.transaction_repository = transaction_repository
        self.task_reward_repository = task_reward_repository

    async def create_group(self, owner_user_id: uuid.UUID, name: str) -> FamilyGroup:
        owner = await self.user_repository.get(owner_user_id)
        if owner is None:
            raise NotFoundError("Foydalanuvchi topilmadi")
        if owner.family_group_id is not None:
            raise ConflictError("Siz allaqachon oila guruhiga a'zosiz")

        group = FamilyGroup(name=name, owner_user_id=owner_user_id)
        group = await self.family_group_repository.add(group)
        owner.family_group_id = group.id
        await self.family_group_repository.commit()
        return group

    async def join_group(self, user_id: uuid.UUID, group_id: uuid.UUID) -> FamilyGroup:
        group = await self.family_group_repository.get(group_id)
        if group is None:
            raise NotFoundError("Oila guruhi topilmadi")

        user = await self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi")
        if user.family_group_id is not None:
            raise ConflictError("Siz allaqachon oila guruhiga a'zosiz")

        user.family_group_id = group.id
        await self.family_group_repository.commit()
        return group

    async def get_my_group_with_members(self, user_id: uuid.UUID) -> tuple[FamilyGroup, list[User]]:
        user = await self.user_repository.get(user_id)
        if user is None or user.family_group_id is None:
            raise NotFoundError("Siz hech qanday oila guruhiga a'zo emassiz")

        group = await self.family_group_repository.get(user.family_group_id)
        members = await self.family_group_repository.list_members(user.family_group_id)
        return group, members

    async def send_allowance(
        self, parent_user_id: uuid.UUID, child_wallet_id: uuid.UUID, amount: Decimal, note: str | None
    ) -> Transaction:
        parent = await self.user_repository.get(parent_user_id)
        wallet = await self.wallet_repository.get(child_wallet_id)
        if parent is None or wallet is None:
            raise NotFoundError("Foydalanuvchi yoki hamyon topilmadi")

        child = await self.user_repository.get(wallet.user_id)
        if child is None or parent.family_group_id is None or child.family_group_id != parent.family_group_id:
            raise UnauthorizedError("Bu hamyon sizning oila guruhingizga tegishli emas")

        transaction = Transaction(
            user_id=wallet.user_id,
            wallet_id=child_wallet_id,
            type=TransactionType.INCOME,
            amount=amount,
            currency=wallet.currency,
            note=note or "Pocket money (ota-ona)",
            source=TransactionSource.MANUAL,
            occurred_at=datetime.now(timezone.utc),
        )
        wallet.balance = Decimal(wallet.balance) + amount
        wallet.version += 1

        transaction = await self.transaction_repository.add(transaction)
        await self.transaction_repository.commit()
        return transaction

    async def create_task(
        self, parent_user_id: uuid.UUID, assigned_to_user_id: uuid.UUID, title: str, reward_amount: Decimal
    ) -> TaskReward:
        parent = await self.user_repository.get(parent_user_id)
        child = await self.user_repository.get(assigned_to_user_id)
        if parent is None or child is None or parent.family_group_id is None:
            raise NotFoundError("Foydalanuvchi topilmadi")
        if child.family_group_id != parent.family_group_id:
            raise UnauthorizedError("Bu foydalanuvchi sizning oila guruhingizga tegishli emas")

        task = TaskReward(
            family_group_id=parent.family_group_id,
            assigned_to_user_id=assigned_to_user_id,
            created_by_user_id=parent_user_id,
            title=title,
            reward_amount=reward_amount,
        )
        task = await self.task_reward_repository.add(task)
        await self.task_reward_repository.commit()
        return task

    async def list_family_tasks(self, user_id: uuid.UUID) -> list[TaskReward]:
        user = await self.user_repository.get(user_id)
        if user is None or user.family_group_id is None:
            raise NotFoundError("Siz hech qanday oila guruhiga a'zo emassiz")
        return await self.task_reward_repository.list_for_family(user.family_group_id)

    async def mark_task_done(self, user_id: uuid.UUID, task_id: uuid.UUID) -> TaskReward:
        task = await self.task_reward_repository.get(task_id)
        if task is None or task.assigned_to_user_id != user_id:
            raise NotFoundError("Vazifa topilmadi")
        task.status = TaskRewardStatus.DONE
        await self.task_reward_repository.commit()
        return task

    async def approve_task(self, parent_user_id: uuid.UUID, task_id: uuid.UUID, wallet_id: uuid.UUID) -> TaskReward:
        task = await self.task_reward_repository.get(task_id)
        if task is None or task.created_by_user_id != parent_user_id:
            raise NotFoundError("Vazifa topilmadi")
        if task.status != TaskRewardStatus.DONE:
            raise ConflictError("Vazifa hali bajarilgan deb belgilanmagan")

        await self.send_allowance(parent_user_id, wallet_id, Decimal(task.reward_amount), f"Vazifa mukofoti: {task.title}")
        task.status = TaskRewardStatus.APPROVED
        await self.task_reward_repository.commit()
        return task
