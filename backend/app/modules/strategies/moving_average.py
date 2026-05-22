from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import TradeAction


DEFAULT_MOVING_AVERAGE_WINDOW = 200


@dataclass(frozen=True)
class MovingAverageDecision:
    action: TradeAction
    symbol: str
    reason: str


class MovingAverageStrategy:
    source_name = "MovingAverageStrategy"

    def decide(
        self,
        *,
        symbol: str,
        price: Decimal,
        moving_average: Decimal | None,
        position_quantity: Decimal | None,
        window: int = DEFAULT_MOVING_AVERAGE_WINDOW,
    ) -> MovingAverageDecision:
        if moving_average is None:
            return MovingAverageDecision(
                action=TradeAction.HOLD,
                symbol=symbol,
                reason=(
                    f"Moving average unavailable until {window} bars are available."
                ),
            )

        has_position = position_quantity is not None and position_quantity > 0
        if price > moving_average and not has_position:
            return MovingAverageDecision(
                action=TradeAction.BUY,
                symbol=symbol,
                reason="SPY price is above moving average and no position exists.",
            )
        if price > moving_average and has_position:
            return MovingAverageDecision(
                action=TradeAction.HOLD,
                symbol=symbol,
                reason="SPY price is above moving average and position already exists.",
            )
        if price < moving_average and has_position:
            return MovingAverageDecision(
                action=TradeAction.SELL,
                symbol=symbol,
                reason="SPY price is below moving average and position exists.",
            )
        if price < moving_average:
            return MovingAverageDecision(
                action=TradeAction.HOLD,
                symbol=symbol,
                reason="SPY price is below moving average and no position exists.",
            )
        return MovingAverageDecision(
            action=TradeAction.HOLD,
            symbol=symbol,
            reason="SPY price is equal to moving average.",
        )
