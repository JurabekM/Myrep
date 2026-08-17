"""Application configuration.

All settings are environment-driven (12-factor). Secrets never have real
defaults — production deployment must provide them via env / Docker secrets.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, MongoDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "AI Business Advisor Uzbekistan"
    environment: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # --- Security ---
    secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    password_min_length: int = 8
    two_fa_issuer: str = "AI Business Advisor UZ"

    # --- MongoDB ---
    mongo_dsn: MongoDsn = Field(default="mongodb://localhost:27017")
    mongo_db_name: str = "ai_advisor"

    # --- Redis ---
    redis_dsn: RedisDsn = Field(default="redis://localhost:6379/0")

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None

    # --- RabbitMQ / Celery ---
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- Rate limiting (per-minute, overridden per plan) ---
    rate_limit_default: int = 60
    rate_limit_auth: int = 10

    # --- AI providers (all optional; ModelRouter skips unconfigured ones) ---
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None
    deepseek_api_key: SecretStr | None = None
    mistral_api_key: SecretStr | None = None
    llama_api_base: str | None = None  # OpenAI-compatible endpoint
    llama_api_key: SecretStr | None = None
    qwen_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"

    default_chat_model: str = "openai:gpt-4o"
    default_embedding_model: str = "openai:text-embedding-3-small"
    embedding_dimensions: int = 1536

    # --- Files ---
    max_upload_size_mb: int = 25
    allowed_upload_extensions: frozenset[str] = frozenset(
        {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".png", ".jpg", ".jpeg"}
    )

    # --- Observability ---
    sentry_dsn: str | None = None
    log_level: str = "INFO"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # env-supplied
