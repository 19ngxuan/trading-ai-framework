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
    market_data_provider: str = "csv"
    alpaca_api_key_id: str | None = None
    alpaca_api_secret_key: str | None = None
    alpaca_data_base_url: str = "https://data.alpaca.markets"
    alpaca_data_feed: str = "iex"
    alpaca_data_adjustment: str = "all"
    alpaca_request_timeout_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_scheduler_config(self) -> "Settings":
        if self.scheduler_enabled and self.scheduler_interval_seconds <= 0:
            raise ValueError(
                "SCHEDULER_INTERVAL_SECONDS must be greater than 0 when scheduler is enabled."
            )
        if self.market_data_provider not in {"csv", "alpaca"}:
            raise ValueError("MARKET_DATA_PROVIDER must be either 'csv' or 'alpaca'.")
        if self.alpaca_request_timeout_seconds <= 0:
            raise ValueError("ALPACA_REQUEST_TIMEOUT_SECONDS must be greater than 0.")
        if self.market_data_provider == "alpaca" and (
            not self.alpaca_api_key_id or not self.alpaca_api_secret_key
        ):
            raise ValueError(
                "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY are required when MARKET_DATA_PROVIDER=alpaca."
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
