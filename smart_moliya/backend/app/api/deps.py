import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.debt_repository import DebtRepository
from app.repositories.family_group_repository import FamilyGroupRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.loan_repository import LoanRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.task_reward_repository import TaskRewardRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_challenge_repository import UserChallengeRepository
from app.repositories.user_progress_repository import UserProgressRepository
from app.repositories.user_repository import UserRepository
from app.repositories.wallet_repository import WalletRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentifikatsiya talab qilinadi",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_error

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_error

    user = await UserRepository(db).get(uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_wallet_repository(db: DbSession) -> WalletRepository:
    return WalletRepository(db)


def get_transaction_repository(db: DbSession) -> TransactionRepository:
    return TransactionRepository(db)


def get_budget_repository(db: DbSession) -> BudgetRepository:
    return BudgetRepository(db)


def get_goal_repository(db: DbSession) -> GoalRepository:
    return GoalRepository(db)


def get_loan_repository(db: DbSession) -> LoanRepository:
    return LoanRepository(db)


def get_debt_repository(db: DbSession) -> DebtRepository:
    return DebtRepository(db)


def get_category_repository(db: DbSession) -> CategoryRepository:
    return CategoryRepository(db)


def get_payment_repository(db: DbSession) -> PaymentRepository:
    return PaymentRepository(db)


def get_achievement_repository(db: DbSession) -> AchievementRepository:
    return AchievementRepository(db)


def get_user_progress_repository(db: DbSession) -> UserProgressRepository:
    return UserProgressRepository(db)


def get_challenge_repository(db: DbSession) -> ChallengeRepository:
    return ChallengeRepository(db)


def get_user_challenge_repository(db: DbSession) -> UserChallengeRepository:
    return UserChallengeRepository(db)


def get_family_group_repository(db: DbSession) -> FamilyGroupRepository:
    return FamilyGroupRepository(db)


def get_task_reward_repository(db: DbSession) -> TaskRewardRepository:
    return TaskRewardRepository(db)
