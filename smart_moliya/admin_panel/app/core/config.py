from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Smart Moliya Admin"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://smartmoliya:smartmoliya@localhost:5432/smartmoliya"

    # Admin kirish ma'lumotlari - production'da .env orqali MAJBURIY almashtirilsin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_SECRET_KEY: str = "change-me-admin-secret"
    SESSION_EXPIRE_HOURS: int = 8


settings = Settings()
