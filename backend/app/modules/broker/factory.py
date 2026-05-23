from app.core.config import Settings
from app.modules.broker.alpaca_broker_adapter import AlpacaPaperTradingAdapter
from app.modules.broker.broker_adapter import BrokerAdapter
from app.modules.broker.errors import BrokerConfigurationError


def create_broker_adapter(settings: Settings) -> BrokerAdapter:
    if not settings.alpaca_paper_trading_enabled:
        raise BrokerConfigurationError("Alpaca paper trading is disabled.")
    return AlpacaPaperTradingAdapter(
        api_key_id=settings.alpaca_api_key_id or "",
        api_secret_key=settings.alpaca_api_secret_key or "",
        base_url=settings.alpaca_trading_base_url,
        timeout_seconds=settings.alpaca_order_timeout_seconds,
    )
