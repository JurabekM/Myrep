from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Smart Moliya AI Service"
    ENVIRONMENT: str = "development"
    MODEL_DIR: str = "app/models/weights"


settings = Settings()
