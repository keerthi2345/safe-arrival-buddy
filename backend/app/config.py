from datetime import timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Safe-Arrival Buddy"
    database_url: str = "sqlite:///./sab.db"
    secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    model_config = SettingsConfigDict(env_file=".env")
    frontend_url: str = "http://localhost:5173"
    confirm_token_expire_hours: int = 48
    max_buddies: int = 5
    default_grace_minutes: int = 10
    max_active_trips: int = 3
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    scheduler_enabled: bool = True
    check_interval_seconds: int = 30
    max_delivery_attempts: int = 3
    escalation_minutes: int = 5
    demo_mode: bool = False
    brevo_api_key: str = ""

    @property
    def minute(self) -> timedelta:
        # in demo mode, one "minute" of grace/escalation lasts one second
        return timedelta(seconds=1) if self.demo_mode else timedelta(minutes=1)

    @property
    def tick_seconds(self) -> int:
        if self.demo_mode:
            return min(self.check_interval_seconds, 5)
        return self.check_interval_seconds

settings = Settings()