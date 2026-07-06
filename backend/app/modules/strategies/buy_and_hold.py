from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import TradeAction


@dataclass(frozen=True)
class StrategyDecision:
    action: TradeAction
    symbol: str
    reason: str


class BuyAndHoldStrategy:
    source_name = "BuyAndHoldStrategy"

    def decide(
        self, symbol: str, position_quantity: Decimal | None
    ) -> StrategyDecision:
        if position_quantity is None or position_quantity == 0:
            return StrategyDecision(
                action=TradeAction.BUY,
                symbol=symbol,
                reason=(
                    f"No current {symbol} position exists; buy and hold enters once."
                ),
            )
        return StrategyDecision(
            action=TradeAction.HOLD,
            symbol=symbol,
            reason=f"Existing {symbol} position is already held.",
        )
