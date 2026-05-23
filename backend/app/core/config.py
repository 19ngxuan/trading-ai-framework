from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading Lab API"
    app_version: str = "0.1.0"
    database_url: str | None = None
    test_database_url: str | None = None
    backend_cors_origins: str = "http://localhost:5173"
    scheduler_enabled: bool = False
    scheduler_interval_seconds: int = 60
    scheduler_job_id: str = "historical_step_scheduler"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_scheduler_config(self) -> "Settings":
        if self.scheduler_enabled and self.scheduler_interval_seconds <= 0:
            raise ValueError(
                "SCHEDULER_INTERVAL_SECONDS must be greater than 0 when scheduler is enabled."
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
