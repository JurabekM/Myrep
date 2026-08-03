from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration, loaded from environment variables / .env.

    Every third-party integration is optional: the app must run and be fully testable
    with none of the *_API_KEY values set (mock providers are used instead).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./dehqon.db"

    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    auth_otp_mode: str = "demo"  # "demo" | "sms"
    sms_provider_api_key: str | None = None
    weather_provider_api_key: str | None = None
    crop_diagnosis_model_endpoint: str | None = None

    cors_allow_origins: str = "*"
    rate_limit_default: str = "60/minute"

    max_upload_image_mb: int = 8

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
