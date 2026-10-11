from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_PREFIX = "dev-only"  # noqa: S105 - bu parol emas, dev belgisi


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OMBORAI_", env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://omborai_app:omborai_app@localhost:5432/omborai"
    jwt_secret: str = f"{DEV_SECRET_PREFIX}-change-me-please-32-bytes-min"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    redis_url: str | None = None

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @model_validator(mode="after")
    def _check_prod_secret(self) -> "Settings":
        if self.is_prod and (self.jwt_secret.startswith(DEV_SECRET_PREFIX) or len(self.jwt_secret) < 32):
            raise ValueError(
                "Productionda OMBORAI_JWT_SECRET kamida 32 belgili va dev qiymatsiz bo'lishi kerak"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
