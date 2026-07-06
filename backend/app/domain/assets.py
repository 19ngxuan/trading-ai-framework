SUPPORTED_EQUITY_SYMBOLS: tuple[str, ...] = (
    "SPY",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "TSLA",
)

SPY_SYMBOL = "SPY"


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def is_supported_equity_symbol(symbol: str) -> bool:
    return normalize_symbol(symbol) in SUPPORTED_EQUITY_SYMBOLS
