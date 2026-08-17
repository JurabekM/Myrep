import uuid

from pydantic import BaseModel


class ProgressRead(BaseModel):
    xp: int
    level: int
    current_streak: int
    longest_streak: int


class LeaderboardEntry(BaseModel):
    user_id: uuid.UUID
    xp: int
    level: int


class BadgeInfo(BaseModel):
    code: str
    name: str
    description: str
    xp_reward: int
