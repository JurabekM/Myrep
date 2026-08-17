import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentUser,
    get_family_group_repository,
    get_task_reward_repository,
    get_transaction_repository,
    get_user_repository,
    get_wallet_repository,
)
from app.repositories.family_group_repository import FamilyGroupRepository
from app.repositories.task_reward_repository import TaskRewardRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.family import (
    AllowanceRequest,
    FamilyGroupCreate,
    FamilyGroupRead,
    FamilyGroupWithMembers,
    FamilyMemberRead,
    TaskRewardApprove,
    TaskRewardCreate,
    TaskRewardRead,
)
from app.schemas.transaction import TransactionRead
from app.services.family_service import FamilyService

router = APIRouter(prefix="/family", tags=["family"])


def get_service(
    family_repo: Annotated[FamilyGroupRepository, Depends(get_family_group_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    wallet_repo: Annotated[WalletRepository, Depends(get_wallet_repository)],
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    task_repo: Annotated[TaskRewardRepository, Depends(get_task_reward_repository)],
) -> FamilyService:
    return FamilyService(family_repo, user_repo, wallet_repo, txn_repo, task_repo)


@router.post("/groups", response_model=FamilyGroupRead, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: FamilyGroupCreate, current_user: CurrentUser, service: Annotated[FamilyService, Depends(get_service)]
):
    group = await service.create_group(current_user.id, payload.name)
    return FamilyGroupRead.model_validate(group)


@router.post("/groups/{group_id}/join", response_model=FamilyGroupRead)
async def join_group(
    group_id: uuid.UUID, current_user: CurrentUser, service: Annotated[FamilyService, Depends(get_service)]
):
    group = await service.join_group(current_user.id, group_id)
    return FamilyGroupRead.model_validate(group)


@router.get("/groups/me", response_model=FamilyGroupWithMembers)
async def get_my_group(current_user: CurrentUser, service: Annotated[FamilyService, Depends(get_service)]):
    group, members = await service.get_my_group_with_members(current_user.id)
    return FamilyGroupWithMembers(
        group=FamilyGroupRead.model_validate(group),
        members=[FamilyMemberRead.model_validate(m) for m in members],
    )


@router.post("/allowance", response_model=TransactionRead)
async def send_allowance(
    payload: AllowanceRequest, current_user: CurrentUser, service: Annotated[FamilyService, Depends(get_service)]
):
    transaction = await service.send_allowance(
        current_user.id, payload.child_wallet_id, payload.amount, payload.note
    )
    return TransactionRead.model_validate(transaction)


@router.get("/tasks", response_model=list[TaskRewardRead])
async def list_family_tasks(current_user: CurrentUser, service: Annotated[FamilyService, Depends(get_service)]):
    tasks = await service.list_family_tasks(current_user.id)
    return [TaskRewardRead.model_validate(t) for t in tasks]


@router.post("/tasks", response_model=TaskRewardRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskRewardCreate, current_user: CurrentUser, service: Annotated[FamilyService, Depends(get_service)]
):
    task = await service.create_task(
        current_user.id, payload.assigned_to_user_id, payload.title, payload.reward_amount
    )
    return TaskRewardRead.model_validate(task)


@router.post("/tasks/{task_id}/done", response_model=TaskRewardRead)
async def mark_task_done(
    task_id: uuid.UUID, current_user: CurrentUser, service: Annotated[FamilyService, Depends(get_service)]
):
    task = await service.mark_task_done(current_user.id, task_id)
    return TaskRewardRead.model_validate(task)


@router.post("/tasks/{task_id}/approve", response_model=TaskRewardRead)
async def approve_task(
    task_id: uuid.UUID,
    payload: TaskRewardApprove,
    current_user: CurrentUser,
    service: Annotated[FamilyService, Depends(get_service)],
):
    task = await service.approve_task(current_user.id, task_id, payload.wallet_id)
    return TaskRewardRead.model_validate(task)
