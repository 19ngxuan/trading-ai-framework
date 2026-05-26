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
    paper_trading_scheduler_enabled: bool = False
    paper_trading_scheduler_interval_seconds: int = 60
    paper_trading_scheduler_job_id: str = "paper_trading_scheduler"
    paper_trading_daily_evaluation_time: str = "15:55"
    paper_trading_test_mode_enabled: bool = False
    market_data_provider: str = "csv"
    alpaca_api_key_id: str | None = None
    alpaca_api_secret_key: str | None = None
    alpaca_data_base_url: str = "https://data.alpaca.markets"
    alpaca_data_feed: str = "iex"
    alpaca_data_adjustment: str = "all"
    alpaca_request_timeout_seconds: int = 10
    alpaca_paper_trading_enabled: bool = False
    alpaca_trading_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_order_timeout_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_scheduler_config(self) -> "Settings":
        if self.scheduler_enabled and self.scheduler_interval_seconds <= 0:
            raise ValueError(
                "SCHEDULER_INTERVAL_SECONDS must be greater than 0 when scheduler is enabled."
            )
        if (
            self.paper_trading_scheduler_enabled
            and self.paper_trading_scheduler_interval_seconds <= 0
        ):
            raise ValueError(
                "PAPER_TRADING_SCHEDULER_INTERVAL_SECONDS must be greater than 0 when paper trading scheduler is enabled."
            )
        if self.paper_trading_scheduler_enabled and not _valid_hh_mm(
            self.paper_trading_daily_evaluation_time
        ):
            raise ValueError(
                "PAPER_TRADING_DAILY_EVALUATION_TIME must use HH:MM 24-hour format."
            )
        if self.paper_trading_scheduler_enabled and not self.alpaca_paper_trading_enabled:
            raise ValueError(
                "ALPACA_PAPER_TRADING_ENABLED must be true when paper trading scheduler is enabled."
            )
        if self.market_data_provider not in {"csv", "alpaca"}:
            raise ValueError("MARKET_DATA_PROVIDER must be either 'csv' or 'alpaca'.")
        if self.alpaca_request_timeout_seconds <= 0:
            raise ValueError("ALPACA_REQUEST_TIMEOUT_SECONDS must be greater than 0.")
        if self.alpaca_order_timeout_seconds <= 0:
            raise ValueError("ALPACA_ORDER_TIMEOUT_SECONDS must be greater than 0.")
        if self.alpaca_trading_base_url != "https://paper-api.alpaca.markets":
            raise ValueError(
                "ALPACA_TRADING_BASE_URL must be https://paper-api.alpaca.markets."
            )
        if self.market_data_provider == "alpaca" and (
            not self.alpaca_api_key_id or not self.alpaca_api_secret_key
        ):
            raise ValueError(
                "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY are required when MARKET_DATA_PROVIDER=alpaca."
            )
        if self.alpaca_paper_trading_enabled and (
            not self.alpaca_api_key_id or not self.alpaca_api_secret_key
        ):
            raise ValueError(
                "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY are required when ALPACA_PAPER_TRADING_ENABLED=true."
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


def _valid_hh_mm(value: str) -> bool:
    parts = value.split(":")
    if len(parts) != 2:
        return False
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59
