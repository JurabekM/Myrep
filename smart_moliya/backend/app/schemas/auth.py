from pydantic import BaseModel, Field

from app.models.enums import Language


class RegisterRequest(BaseModel):
    phone: str = Field(min_length=9, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = None
    language: Language = Language.UZ


class LoginRequest(BaseModel):
    phone: str
    password: str
    device_id: str = Field(min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    refresh_token: str
    device_id: str = Field(min_length=1, max_length=255)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OtpRequest(BaseModel):
    phone: str = Field(min_length=9, max_length=20)


class OtpRequestResponse(BaseModel):
    message: str
    dev_code: str | None = None  # faqat non-production: SMS o'rniga kod shu yerda qaytadi


class OtpVerifyRequest(BaseModel):
    phone: str = Field(min_length=9, max_length=20)
    code: str = Field(min_length=4, max_length=8)
    device_id: str = Field(min_length=1, max_length=255)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)
    device_id: str = Field(min_length=1, max_length=255)
