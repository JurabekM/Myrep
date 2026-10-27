"""Server sozlamalari — muhit o'zgaruvchilari (`ZANJIR_*`) yoki `.env`; maxfiy qiymatlar commit qilinmaydi."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Argon2Params(BaseSettings):
    """argon2id parametrlari (RFC 9106, 2-tavsiya: t=3, m=64 MiB, p=4). Testlarda kamaytiriladi."""

    model_config = SettingsConfigDict(env_prefix="ZANJIR_ARGON2_")
    time_cost: int = 3
    memory_kib: int = 65536
    parallelism: int = 4


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZANJIR_", env_file=".env", extra="ignore")

    database_url: SecretStr = Field(description="postgresql+asyncpg://...")
    jwt_secret: SecretStr = Field(min_length=32, description="HS256 kaliti, kamida 32 belgi")
    access_ttl_seconds: int = 15 * 60
    refresh_ttl_seconds: int = 30 * 24 * 3600
    invite_ttl_hours_max: int = 7 * 24
    # Yangi laboratoriyani o'zi ro'yxatdan o'tkazishi (MVP'da prod uchun yopiq; ADR-0011).
    registration_open: bool = False
    cors_origins: list[str] = []
    max_body_bytes: int = 5 * 1024 * 1024
    rate_limit_auth_per_minute: int = 10
    rate_limit_default_per_minute: int = 300
    sync_max_ops: int = 500
    sync_pull_limit: int = 500
    argon2: Argon2Params = Field(default_factory=Argon2Params)
    sms_otp_enabled: bool = False
    # `/metrics` faqat shu token bilan (`Authorization: Bearer ...`); berilmasa — o'chiq (404). ADR-0014.
    metrics_token: SecretStr | None = None
    # Bitta telefon raqamiga ketma-ket noto'g'ri parollar (IP dan qat'i nazar) — oyna ichida chegaradan keyin 429.
    login_failures_max: int = 10
    login_failures_window_seconds: int = 15 * 60
    # Qurilma soati serverdan shuncha oldinda bo'lsa push rad etiladi (LWW'ni "kelajak" vaqt bilan egallab olmaslik).
    max_clock_skew_seconds: int = 10 * 60
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
