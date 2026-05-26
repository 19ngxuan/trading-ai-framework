from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import TradeAction


@dataclass(frozen=True)
class PaperTradingSmokeTestDecision:
    action: TradeAction
    symbol: str
    reason: str


class PaperTradingSmokeTestStrategy:
    source_name = "PaperTradingSmokeTestStrategy"

    def decide(
        self, symbol: str, position_quantity: Decimal | None
    ) -> PaperTradingSmokeTestDecision:
        if position_quantity is not None and position_quantity > 0:
            return PaperTradingSmokeTestDecision(
                action=TradeAction.SELL,
                symbol=symbol,
                reason=(
                    "Smoke-test position exists; sell the current local SPY position."
                ),
            )
        return PaperTradingSmokeTestDecision(
            action=TradeAction.BUY,
            symbol=symbol,
            reason="No smoke-test SPY position exists; buy exactly one share.",
        )
