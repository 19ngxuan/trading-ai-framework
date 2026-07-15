from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading Lab API"
    app_version: str = "0.1.0"
    database_url: str | None = None
    test_database_url: str | None = None
    backend_cors_origins: str = "http://localhost:5173"
    app_auth_enabled: bool = False
    app_auth_username: str | None = None
    app_auth_password_hash: str | None = None
    app_auth_jwt_secret: str | None = None
    app_auth_token_expire_minutes: int = 720
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
    scadsai_llm_enabled: bool = False
    scadsai_api_key: str | None = None
    scadsai_base_url: str = "https://llm.scads.ai/v1"
    scadsai_request_timeout_seconds: int = 30
    scadsai_allowed_models: str = "alias-ha,meta-llama/Llama-3.3-70B-Instruct,meta-llama/Llama-3.1-8B-Instruct,alias-reasoning,alias-huge,alias-huge-no-thinking,Qwen/Qwen3-VL-8B-Instruct,alias-vision,openGPT-X/Teuken-7B-instruct-v0.6,Qwen/Qwen3-Coder-30B-A3B-Instruct,alias-code,google/gemma-4-31B-it,openai/gpt-oss-120b,moonshotai/Kimi-K2.6,MiniMaxAI/MiniMax-M2.7"
    scadsai_default_model: str = "meta-llama/Llama-3.3-70B-Instruct"
    event_scanner_enabled: bool = False
    event_scanner_interval_seconds: int = 900
    event_news_provider: str = "alpaca"
    event_lookback_minutes: int = 30
    event_relevance_threshold: float = 0.65
    event_news_limit: int = 50
    research_data_provider: str = "parameters"
    fmp_api_key: str | None = None
    fmp_base_url: str = "https://financialmodelingprep.com/stable"
    fmp_request_timeout_seconds: int = 10
    yahoo_base_url: str = "https://query1.finance.yahoo.com"
    yahoo_request_timeout_seconds: int = 10
    multi_agent_news_lookback_hours: int = 24
    multi_agent_news_limit: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_scheduler_config(self) -> "Settings":
        if self.scheduler_enabled and self.scheduler_interval_seconds <= 0:
            raise ValueError(
                "SCHEDULER_INTERVAL_SECONDS must be greater than 0 when scheduler is enabled."
            )
        if self.app_auth_token_expire_minutes <= 0:
            raise ValueError("APP_AUTH_TOKEN_EXPIRE_MINUTES must be greater than 0.")
        if self.app_auth_enabled and not self.app_auth_username:
            raise ValueError("APP_AUTH_USERNAME is required when APP_AUTH_ENABLED=true.")
        if self.app_auth_enabled and not self.app_auth_password_hash:
            raise ValueError(
                "APP_AUTH_PASSWORD_HASH is required when APP_AUTH_ENABLED=true."
            )
        if self.app_auth_enabled and not self.app_auth_jwt_secret:
            raise ValueError(
                "APP_AUTH_JWT_SECRET is required when APP_AUTH_ENABLED=true."
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
        if self.scadsai_request_timeout_seconds <= 0:
            raise ValueError("SCADSAI_REQUEST_TIMEOUT_SECONDS must be greater than 0.")
        if not self.scadsai_base_url.startswith("https://"):
            raise ValueError("SCADSAI_BASE_URL must use HTTPS.")
        if self.scadsai_llm_enabled and not self.scadsai_api_key:
            raise ValueError(
                "SCADSAI_API_KEY is required when SCADSAI_LLM_ENABLED=true."
            )
        if self.scadsai_default_model not in self.scadsai_allowed_model_list:
            raise ValueError(
                "SCADSAI_DEFAULT_MODEL must be included in SCADSAI_ALLOWED_MODELS."
            )
        if self.event_scanner_interval_seconds <= 0:
            raise ValueError("EVENT_SCANNER_INTERVAL_SECONDS must be greater than 0.")
        if self.event_news_provider != "alpaca":
            raise ValueError("EVENT_NEWS_PROVIDER must be 'alpaca'.")
        if self.event_lookback_minutes <= 0:
            raise ValueError("EVENT_LOOKBACK_MINUTES must be greater than 0.")
        if not 0 <= self.event_relevance_threshold <= 1:
            raise ValueError(
                "EVENT_RELEVANCE_THRESHOLD must be between 0 and 1."
            )
        if not 1 <= self.event_news_limit <= 50:
            raise ValueError("EVENT_NEWS_LIMIT must be between 1 and 50.")
        if self.event_scanner_enabled and (
            not self.alpaca_api_key_id or not self.alpaca_api_secret_key
        ):
            raise ValueError(
                "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY are required when EVENT_SCANNER_ENABLED=true."
            )
        if self.research_data_provider not in {"parameters", "fmp"}:
            raise ValueError("RESEARCH_DATA_PROVIDER must be either 'parameters' or 'fmp'.")
        if self.research_data_provider == "fmp" and not self.fmp_api_key:
            raise ValueError("FMP_API_KEY is required when RESEARCH_DATA_PROVIDER=fmp.")
        if not self.fmp_base_url.startswith("https://"):
            raise ValueError("FMP_BASE_URL must use HTTPS.")
        if self.fmp_request_timeout_seconds <= 0:
            raise ValueError("FMP_REQUEST_TIMEOUT_SECONDS must be greater than 0.")
        if not self.yahoo_base_url.startswith("https://"):
            raise ValueError("YAHOO_BASE_URL must use HTTPS.")
        if self.yahoo_request_timeout_seconds <= 0:
            raise ValueError("YAHOO_REQUEST_TIMEOUT_SECONDS must be greater than 0.")
        if self.multi_agent_news_lookback_hours <= 0:
            raise ValueError("MULTI_AGENT_NEWS_LOOKBACK_HOURS must be greater than 0.")
        if not 1 <= self.multi_agent_news_limit <= 50:
            raise ValueError("MULTI_AGENT_NEWS_LIMIT must be between 1 and 50.")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def scadsai_allowed_model_list(self) -> list[str]:
        return [
            model.strip()
            for model in self.scadsai_allowed_models.split(",")
            if model.strip()
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
