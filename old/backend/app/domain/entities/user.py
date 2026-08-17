"""User domain entity and related enums."""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class UserRole(StrEnum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class BusinessType(StrEnum):
    YTT = "ytt"  # Yakka tartibdagi tadbirkor
    MCHJ = "mchj"  # Mas'uliyati cheklangan jamiyat
    MICROFIRM = "microfirm"
    FREELANCER = "freelancer"
    STARTUP = "startup"
    OTHER = "other"


class BusinessProfile(BaseModel):
    """Profile the AI uses to personalise every answer."""

    industry: str | None = None
    business_type: BusinessType | None = None
    experience_years: int | None = Field(default=None, ge=0, le=80)
    goals: list[str] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    annual_revenue_uzs: int | None = Field(default=None, ge=0)
    employees: int | None = Field(default=None, ge=0)
    location: str | None = None  # viloyat/shahar


class User(BaseModel):
    id: str
    email: EmailStr
    phone: str | None = None
    full_name: str
    password_hash: str
    role: UserRole = UserRole.USER
    plan: Plan = Plan.FREE
    locale: str = "uz-Latn"
    is_active: bool = True
    email_verified: bool = False
    two_fa_enabled: bool = False
    two_fa_secret: str | None = None
    profile: BusinessProfile = Field(default_factory=BusinessProfile)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def can_access_plan_feature(self, required: Plan) -> bool:
        order = [Plan.FREE, Plan.PRO, Plan.BUSINESS, Plan.ENTERPRISE]
        return order.index(self.plan) >= order.index(required)
