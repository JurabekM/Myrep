import asyncio
import uuid
from datetime import date, timedelta

from app.models.achievement import Achievement
from app.models.user_progress import UserProgress
from app.services.gamification_service import GamificationService


class FakeProgressRepository:
    def __init__(self):
        self._store: dict[uuid.UUID, UserProgress] = {}

    async def get_or_create(self, user_id):
        if user_id not in self._store:
            self._store[user_id] = UserProgress(
                user_id=user_id, xp=0, level=1, current_streak=0, longest_streak=0
            )
        return self._store[user_id]

    async def top_by_xp(self, limit=10):
        return sorted(self._store.values(), key=lambda p: p.xp, reverse=True)[:limit]

    async def commit(self):
        pass


class FakeAchievementRepository:
    def __init__(self):
        self._badges: set[tuple[uuid.UUID, str]] = set()

    async def has_badge(self, user_id, badge_code):
        return (user_id, badge_code) in self._badges

    async def add(self, achievement: Achievement):
        self._badges.add((achievement.user_id, achievement.badge_code))
        return achievement

    async def commit(self):
        pass


def test_add_xp_increases_level_at_threshold():
    user_id = uuid.uuid4()
    service = GamificationService(FakeProgressRepository(), FakeAchievementRepository())

    progress = asyncio.run(service.add_xp(user_id, 999))
    assert progress.level == 1

    progress = asyncio.run(service.add_xp(user_id, 1))
    assert progress.xp == 1000
    assert progress.level == 2


def test_award_badge_is_idempotent_and_grants_xp_once():
    user_id = uuid.uuid4()
    service = GamificationService(FakeProgressRepository(), FakeAchievementRepository())

    first = asyncio.run(service.award_badge(user_id, "first_transaction"))
    second = asyncio.run(service.award_badge(user_id, "first_transaction"))

    assert first is True
    assert second is False
    progress = asyncio.run(service.get_profile(user_id))
    assert progress.xp == 50  # first_transaction xp_reward, faqat bir marta qo'shilgan


def test_award_unknown_badge_raises():
    import pytest

    user_id = uuid.uuid4()
    service = GamificationService(FakeProgressRepository(), FakeAchievementRepository())
    with pytest.raises(ValueError):
        asyncio.run(service.award_badge(user_id, "does-not-exist"))


def test_streak_increments_on_consecutive_days():
    user_id = uuid.uuid4()
    progress_repo = FakeProgressRepository()
    service = GamificationService(progress_repo, FakeAchievementRepository())

    progress = asyncio.run(progress_repo.get_or_create(user_id))
    progress.last_activity_date = date.today() - timedelta(days=1)
    progress.current_streak = 3
    progress.longest_streak = 3

    result = asyncio.run(service.record_daily_activity(user_id))
    assert result.current_streak == 4
    assert result.longest_streak == 4


def test_streak_resets_after_gap():
    user_id = uuid.uuid4()
    progress_repo = FakeProgressRepository()
    service = GamificationService(progress_repo, FakeAchievementRepository())

    progress = asyncio.run(progress_repo.get_or_create(user_id))
    progress.last_activity_date = date.today() - timedelta(days=3)
    progress.current_streak = 5
    progress.longest_streak = 5

    result = asyncio.run(service.record_daily_activity(user_id))
    assert result.current_streak == 1
    assert result.longest_streak == 5  # eng uzun streak saqlanib qoladi


def test_streak_same_day_does_not_double_count():
    user_id = uuid.uuid4()
    progress_repo = FakeProgressRepository()
    service = GamificationService(progress_repo, FakeAchievementRepository())

    asyncio.run(service.record_daily_activity(user_id))
    result = asyncio.run(service.record_daily_activity(user_id))
    assert result.current_streak == 1


def test_leaderboard_sorted_by_xp_desc():
    progress_repo = FakeProgressRepository()
    service = GamificationService(progress_repo, FakeAchievementRepository())

    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    asyncio.run(service.add_xp(user_a, 200))
    asyncio.run(service.add_xp(user_b, 500))

    leaderboard = asyncio.run(service.leaderboard())
    assert leaderboard[0].user_id == user_b
    assert leaderboard[1].user_id == user_a
