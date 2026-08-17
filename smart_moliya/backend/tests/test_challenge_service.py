import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.models.enums import ChallengePeriod, ChallengeTargetType, TransactionType
from app.services.challenge_service import ChallengeService
from app.services.gamification_service import GamificationService
from app.models.user_progress import UserProgress


@dataclass
class FakeChallenge:
    id: uuid.UUID
    period: ChallengePeriod
    target_type: ChallengeTargetType
    target_value: Decimal
    xp_reward: int
    start_date: date
    end_date: date


@dataclass
class FakeUserChallenge:
    id: uuid.UUID
    user_id: uuid.UUID
    challenge_id: uuid.UUID
    progress_value: Decimal = Decimal("0")
    completed_at: datetime | None = None


@dataclass
class FakeTransaction:
    type: TransactionType
    amount: Decimal
    occurred_at: datetime


class FakeChallengeRepository:
    def __init__(self, challenges: list[FakeChallenge]):
        self._challenges = {c.id: c for c in challenges}

    async def get(self, challenge_id):
        return self._challenges.get(challenge_id)

    async def list_active(self):
        return list(self._challenges.values())


class FakeUserChallengeRepository:
    def __init__(self):
        self._store: dict[tuple, FakeUserChallenge] = {}

    async def get_for_user_and_challenge(self, user_id, challenge_id):
        return self._store.get((user_id, challenge_id))

    async def add(self, uc: FakeUserChallenge):
        self._store[(uc.user_id, uc.challenge_id)] = uc
        return uc

    async def list_for_user(self, user_id):
        return [uc for (uid, _), uc in self._store.items() if uid == user_id]

    async def commit(self):
        pass


class FakeTransactionRepository:
    def __init__(self, transactions: list[FakeTransaction]):
        self._transactions = transactions

    async def list_between(self, user_id, start, end):
        return [t for t in self._transactions if start <= t.occurred_at <= end]


class FakeProgressRepository:
    def __init__(self):
        self._store: dict[uuid.UUID, UserProgress] = {}

    async def get_or_create(self, user_id):
        if user_id not in self._store:
            self._store[user_id] = UserProgress(user_id=user_id, xp=0, level=1, current_streak=0, longest_streak=0)
        return self._store[user_id]

    async def commit(self):
        pass


class FakeAchievementRepository:
    def __init__(self):
        self._badges = set()

    async def has_badge(self, user_id, badge_code):
        return (user_id, badge_code) in self._badges

    async def add(self, achievement):
        self._badges.add((achievement.user_id, achievement.badge_code))
        return achievement

    async def commit(self):
        pass


def _build_service(challenges, transactions):
    gamification = GamificationService(FakeProgressRepository(), FakeAchievementRepository())
    return ChallengeService(
        FakeChallengeRepository(challenges),
        FakeUserChallengeRepository(),
        FakeTransactionRepository(transactions),
        gamification,
    ), gamification


def test_save_amount_challenge_completes_when_target_reached():
    user_id = uuid.uuid4()
    challenge = FakeChallenge(
        id=uuid.uuid4(),
        period=ChallengePeriod.WEEKLY,
        target_type=ChallengeTargetType.SAVE_AMOUNT,
        target_value=Decimal("100000"),
        xp_reward=200,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
    )
    transactions = [
        FakeTransaction(TransactionType.INCOME, Decimal("500000"), datetime(2026, 7, 2, tzinfo=timezone.utc)),
        FakeTransaction(TransactionType.EXPENSE, Decimal("300000"), datetime(2026, 7, 3, tzinfo=timezone.utc)),
    ]
    service, gamification = _build_service([challenge], transactions)

    asyncio.run(service.join(user_id, challenge.id))
    result = asyncio.run(service.evaluate_progress(user_id, challenge.id))

    assert result.progress_value == Decimal("200000")  # 500000 - 300000
    assert result.completed_at is not None

    profile = asyncio.run(gamification.get_profile(user_id))
    assert profile.xp >= 200  # challenge xp_reward + challenge_completed badge xp


def test_save_amount_challenge_not_completed_below_target():
    user_id = uuid.uuid4()
    challenge = FakeChallenge(
        id=uuid.uuid4(),
        period=ChallengePeriod.WEEKLY,
        target_type=ChallengeTargetType.SAVE_AMOUNT,
        target_value=Decimal("1000000"),
        xp_reward=200,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
    )
    transactions = [
        FakeTransaction(TransactionType.INCOME, Decimal("500000"), datetime(2026, 7, 2, tzinfo=timezone.utc)),
        FakeTransaction(TransactionType.EXPENSE, Decimal("300000"), datetime(2026, 7, 3, tzinfo=timezone.utc)),
    ]
    service, _ = _build_service([challenge], transactions)

    asyncio.run(service.join(user_id, challenge.id))
    result = asyncio.run(service.evaluate_progress(user_id, challenge.id))

    assert result.progress_value == Decimal("200000")
    assert result.completed_at is None


def test_no_spend_days_challenge_counts_days_without_expense():
    user_id = uuid.uuid4()
    challenge = FakeChallenge(
        id=uuid.uuid4(),
        period=ChallengePeriod.WEEKLY,
        target_type=ChallengeTargetType.NO_SPEND_DAYS,
        target_value=Decimal("5"),
        xp_reward=150,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),  # 7 kun
    )
    # faqat 2 kunda xarajat bo'lgan -> 5 kun xarajatsiz
    transactions = [
        FakeTransaction(TransactionType.EXPENSE, Decimal("10000"), datetime(2026, 7, 2, tzinfo=timezone.utc)),
        FakeTransaction(TransactionType.EXPENSE, Decimal("20000"), datetime(2026, 7, 4, tzinfo=timezone.utc)),
    ]
    service, _ = _build_service([challenge], transactions)

    asyncio.run(service.join(user_id, challenge.id))
    result = asyncio.run(service.evaluate_progress(user_id, challenge.id))

    assert result.progress_value == Decimal("5")
    assert result.completed_at is not None


def test_joining_same_challenge_twice_raises_conflict():
    import pytest
    from app.services.exceptions import ConflictError

    user_id = uuid.uuid4()
    challenge = FakeChallenge(
        id=uuid.uuid4(),
        period=ChallengePeriod.MONTHLY,
        target_type=ChallengeTargetType.SAVE_AMOUNT,
        target_value=Decimal("100000"),
        xp_reward=200,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    service, _ = _build_service([challenge], [])

    asyncio.run(service.join(user_id, challenge.id))
    with pytest.raises(ConflictError):
        asyncio.run(service.join(user_id, challenge.id))
