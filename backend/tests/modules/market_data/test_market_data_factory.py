import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.market_data.alpaca_provider import AlpacaMarketDataProvider
from app.modules.market_data.csv_loader import SpyCsvLoader
from app.modules.market_data.factory import create_market_data_provider


def test_default_market_data_provider_is_csv() -> None:
    settings = Settings()

    provider = create_market_data_provider(settings)

    assert isinstance(provider, SpyCsvLoader)


def test_alpaca_provider_requires_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(market_data_provider="alpaca")


def test_invalid_provider_and_timeout_fail_validation() -> None:
    with pytest.raises(ValidationError):
        Settings(market_data_provider="unknown")
    with pytest.raises(ValidationError):
        Settings(alpaca_request_timeout_seconds=0)


def test_factory_returns_alpaca_provider_when_configured() -> None:
    settings = Settings(
        market_data_provider="alpaca",
        alpaca_api_key_id="key",
        alpaca_api_secret_key="secret",
        alpaca_data_base_url="https://data.example.test",
    )

    provider = create_market_data_provider(settings)

    assert isinstance(provider, AlpacaMarketDataProvider)
