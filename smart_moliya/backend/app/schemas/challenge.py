import uuid
from datetime import date, datetime
from decimal import Decimal

from app.models.enums import ChallengePeriod, ChallengeTargetType
from app.schemas.common import ORMModel


class ChallengeRead(ORMModel):
    id: uuid.UUID
    code: str
    title: str
    description: str
    period: ChallengePeriod
    target_type: ChallengeTargetType
    target_value: Decimal
    xp_reward: int
    start_date: date
    end_date: date


class UserChallengeRead(ORMModel):
    id: uuid.UUID
    challenge: ChallengeRead
    progress_value: Decimal
    completed_at: datetime | None
