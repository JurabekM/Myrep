from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Smart Moliya API"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://smartmoliya:smartmoliya@localhost:5432/smartmoliya"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "change-me-in-.env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OTP (SMS orqali kirish)
    OTP_EXPIRE_SECONDS: int = 120
    OTP_MAX_ATTEMPTS: int = 5

    # Google Sign-In: bo'sh bo'lsa mock verifier ishlaydi (faqat non-production)
    GOOGLE_CLIENT_ID: str = ""


settings = Settings()
