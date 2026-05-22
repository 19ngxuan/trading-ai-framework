from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MetricResult:
    total_return: Decimal
    profit_loss: Decimal
    number_of_trades: int
    max_drawdown: Decimal
    buy_and_hold_return: Decimal
    difference_to_buy_and_hold: Decimal


class BasicMetricCalculator:
    def calculate(
        self,
        *,
        initial_capital: Decimal,
        current_portfolio_value: Decimal,
        previous_portfolio_values: list[Decimal],
        number_of_trades: int,
    ) -> MetricResult:
        profit_loss = (current_portfolio_value - initial_capital).quantize(
            Decimal("0.0001")
        )
        total_return = (profit_loss / initial_capital).quantize(Decimal("0.00000001"))
        values = [*previous_portfolio_values, current_portfolio_value]
        max_drawdown = self._max_drawdown(values)
        return MetricResult(
            total_return=total_return,
            profit_loss=profit_loss,
            number_of_trades=number_of_trades,
            max_drawdown=max_drawdown,
            buy_and_hold_return=total_return,
            difference_to_buy_and_hold=Decimal("0"),
        )

    def _max_drawdown(self, values: list[Decimal]) -> Decimal:
        peak: Decimal | None = None
        max_drawdown = Decimal("0")
        for value in values:
            if peak is None or value > peak:
                peak = value
            if peak and peak > 0:
                drawdown = ((value - peak) / peak).quantize(Decimal("0.00000001"))
                if drawdown < max_drawdown:
                    max_drawdown = drawdown
        return max_drawdown
