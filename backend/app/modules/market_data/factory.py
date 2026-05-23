from app.core.config import Settings
from app.modules.market_data.alpaca_provider import AlpacaMarketDataProvider
from app.modules.market_data.csv_loader import SpyCsvLoader
from app.modules.market_data.provider import MarketDataProvider


def create_market_data_provider(settings: Settings) -> MarketDataProvider:
    if settings.market_data_provider == "alpaca":
        return AlpacaMarketDataProvider(
            api_key_id=settings.alpaca_api_key_id or "",
            api_secret_key=settings.alpaca_api_secret_key or "",
            base_url=settings.alpaca_data_base_url,
            feed=settings.alpaca_data_feed,
            adjustment=settings.alpaca_data_adjustment,
            timeout_seconds=settings.alpaca_request_timeout_seconds,
        )
    return SpyCsvLoader()
