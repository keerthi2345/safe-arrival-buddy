from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Safe-Arrival Buddy"
    database_url: str = "sqlite:///./sab.db"
    secret_key: str = "change-me-in-env"
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()