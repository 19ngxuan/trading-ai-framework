class MarketDataProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MarketDataUnavailableError(MarketDataProviderError):
    pass
