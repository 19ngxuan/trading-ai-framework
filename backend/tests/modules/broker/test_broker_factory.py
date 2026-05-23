import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.broker.alpaca_broker_adapter import AlpacaPaperTradingAdapter
from app.modules.broker.errors import BrokerConfigurationError
from app.modules.broker.factory import create_broker_adapter


def test_paper_trading_disabled_by_default() -> None:
    settings = Settings()

    assert settings.alpaca_paper_trading_enabled is False
    with pytest.raises(BrokerConfigurationError):
        create_broker_adapter(settings)


def test_paper_trading_requires_credentials_only_when_enabled() -> None:
    Settings(alpaca_paper_trading_enabled=False)

    with pytest.raises(ValidationError):
        Settings(alpaca_paper_trading_enabled=True)


def test_invalid_order_timeout_and_live_base_url_fail_validation() -> None:
    with pytest.raises(ValidationError):
        Settings(alpaca_order_timeout_seconds=0)

    with pytest.raises(ValidationError):
        Settings(alpaca_trading_base_url="https://api.alpaca.markets")


def test_factory_returns_alpaca_paper_adapter_when_enabled() -> None:
    adapter = create_broker_adapter(
        Settings(
            alpaca_paper_trading_enabled=True,
            alpaca_api_key_id="key",
            alpaca_api_secret_key="secret",
        )
    )

    assert isinstance(adapter, AlpacaPaperTradingAdapter)
