from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_REGEX = r"^\+998\d{9}$"


class OtpRequestIn(BaseModel):
    phone_number: str = Field(..., description="Uzbekistan phone number, e.g. +998901234567")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re

        if not re.match(PHONE_REGEX, v):
            raise ValueError("phone_number must match +998XXXXXXXXX")
        return v


class OtpRequestOut(BaseModel):
    request_id: str
    demo_code_hint: str | None = None


class OtpVerifyIn(BaseModel):
    request_id: str
    code: str = Field(..., min_length=4, max_length=8)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WeatherDayOut(BaseModel):
    epoch_day: int
    temp_min_c: float
    temp_max_c: float
    rain_probability_percent: int
    summary: str


class WeatherOut(BaseModel):
    region: str
    current_temp_c: float
    current_condition: str
    forecast: list[WeatherDayOut]


class DiagnosisResultOut(BaseModel):
    diagnosis_log_id: str
    category: str
    confidence: float
    cause: str
    safe_steps: list[str]
    watch_for: list[str]
    consult_advice: str
    disclaimer: str = "Bu umumiy yo'nalish, yakuniy tashxis emas. Shubha bo'lsa, agronomga murojaat qiling."


class DiagnosisRatingIn(BaseModel):
    diagnosis_log_id: str
    useful: bool


class ListingIn(BaseModel):
    variety: str = Field(..., min_length=1, max_length=100)
    quantity_kg: float = Field(..., gt=0, le=1_000_000)
    price_som: float | None = Field(None, ge=0)
    negotiable: bool = False
    region: str = Field(..., min_length=1, max_length=100)
    availability_date: datetime
    contact_method: str = Field(..., pattern="^(phone|telegram)$")
    contact_value: str = Field(..., min_length=3, max_length=100)
    contact_consent: bool
    group_id: str | None = None

    @field_validator("contact_value")
    @classmethod
    def sanitize_contact(cls, v: str) -> str:
        return v.strip()


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    variety: str
    quantity_kg: float
    price_som: float | None
    negotiable: bool
    region: str
    availability_date: datetime
    photo_path: str | None
    contact_method: str
    contact_value: str | None
    contact_consent: bool
    group_id: str | None
    created_at: datetime


class ListingReportIn(BaseModel):
    reason: str = Field(..., pattern="^(spam|fraud|inappropriate|other)$")
    note: str = Field("", max_length=500)


class SellGroupIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    region: str = Field(..., min_length=1, max_length=100)


class SellGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    region: str
    admin_user_id: str
    created_at: datetime
    aggregated_quantity_kg: float = 0.0


class ErrorOut(BaseModel):
    """Uniform, safe error envelope: never leaks stack traces or internal details."""

    error: str
    detail: str | None = None
