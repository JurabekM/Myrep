"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.entities.user import BusinessProfile, Plan, UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, pattern=r"^\+998\d{9}$")
    locale: str = "uz-Latn"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("Parol harf va raqamlardan iborat bo'lishi kerak")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str = Field(min_length=8, max_length=64)
    totp_code: str | None = Field(default=None, min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TwoFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TwoFAConfirmRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None
    role: UserRole
    plan: Plan
    locale: str
    two_fa_enabled: bool
    profile: BusinessProfile


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    locale: str | None = None
    profile: BusinessProfile | None = None
