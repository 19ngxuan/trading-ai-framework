from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Any

from app.domain.enums import FinalAction, TradeAction


ALL_IN = "ALL_IN"
FIXED_CASH = "FIXED_CASH"
PERCENT_OF_PORTFOLIO = "PERCENT_OF_PORTFOLIO"
FIXED_QUANTITY = "FIXED_QUANTITY"

SUPPORTED_POSITION_SIZING_TYPES = {
    ALL_IN,
    FIXED_CASH,
    PERCENT_OF_PORTFOLIO,
    FIXED_QUANTITY,
}


class PositionSizingConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class PositionSizingResult:
    final_action: FinalAction
    requested_quantity: Decimal | None
    final_quantity: Decimal | None
    sizing_reason: str


def _floor_whole_shares(value: Decimal) -> Decimal:
    return value.to_integral_value(rounding=ROUND_FLOOR)


def _validate_sizing_value(sizing_type: str, sizing_value: Decimal | None) -> None:
    if sizing_type == ALL_IN:
        return
    if sizing_value is None:
        raise PositionSizingConfigurationError(
            f"{sizing_type} requires positionSizingValue."
        )
    if sizing_type == FIXED_CASH and sizing_value <= 0:
        raise PositionSizingConfigurationError("FIXED_CASH requires a positive value.")
    if sizing_type == PERCENT_OF_PORTFOLIO and (
        sizing_value <= 0 or sizing_value > Decimal("1")
    ):
        raise PositionSizingConfigurationError(
            "PERCENT_OF_PORTFOLIO requires a value greater than 0 and less than or equal to 1."
        )
    if sizing_type == FIXED_QUANTITY:
        if sizing_value <= 0 or sizing_value != sizing_value.to_integral_value():
            raise PositionSizingConfigurationError(
                "FIXED_QUANTITY requires a positive whole-number value."
            )


def validate_position_sizing_config(
    sizing_type: str | None,
    sizing_value: Decimal | None,
) -> None:
    normalized_type = sizing_type or ALL_IN
    if normalized_type not in SUPPORTED_POSITION_SIZING_TYPES:
        raise PositionSizingConfigurationError(
            f"Unsupported positionSizingType: {normalized_type}."
        )
    _validate_sizing_value(normalized_type, sizing_value)


def parse_position_sizing_value(parameters_json: dict[str, Any] | None) -> Decimal | None:
    if not parameters_json or "positionSizingValue" not in parameters_json:
        return None
    value = parameters_json["positionSizingValue"]
    if value is None:
        return None
    return Decimal(str(value))


def calculate_position_size(
    action: TradeAction,
    cash: Decimal,
    current_portfolio_value: Decimal | None,
    current_position_quantity: Decimal | None,
    price: Decimal,
    sizing_type: str | None,
    sizing_value: Decimal | None,
) -> PositionSizingResult:
    normalized_type = sizing_type or ALL_IN
    validate_position_sizing_config(normalized_type, sizing_value)

    if price <= 0:
        raise PositionSizingConfigurationError("Execution price must be positive.")

    position_quantity = current_position_quantity or Decimal("0")
    if action is TradeAction.HOLD:
        return PositionSizingResult(
            final_action=FinalAction.HOLD,
            requested_quantity=None,
            final_quantity=None,
            sizing_reason="HOLD_ACTION",
        )

    if action is TradeAction.SELL:
        if position_quantity <= 0:
            return PositionSizingResult(
                final_action=FinalAction.HOLD,
                requested_quantity=None,
                final_quantity=None,
                sizing_reason="NO_POSITION_TO_SELL",
            )
        return PositionSizingResult(
            final_action=FinalAction.SELL,
            requested_quantity=position_quantity,
            final_quantity=position_quantity,
            sizing_reason="SELL_FULL_POSITION",
        )

    affordable_quantity = _floor_whole_shares(cash / price)
    if normalized_type == ALL_IN:
        requested_quantity = affordable_quantity
        quantity = affordable_quantity
        reason = "ALL_IN"
    elif normalized_type == FIXED_CASH:
        assert sizing_value is not None
        target_cash = min(cash, sizing_value)
        requested_quantity = _floor_whole_shares(sizing_value / price)
        quantity = _floor_whole_shares(target_cash / price)
        reason = "FIXED_CASH"
    elif normalized_type == PERCENT_OF_PORTFOLIO:
        assert sizing_value is not None
        portfolio_value = current_portfolio_value if current_portfolio_value is not None else cash
        target_cash = portfolio_value * sizing_value
        requested_quantity = _floor_whole_shares(target_cash / price)
        quantity = _floor_whole_shares(min(cash, target_cash) / price)
        reason = "PERCENT_OF_PORTFOLIO"
    else:
        assert normalized_type == FIXED_QUANTITY
        assert sizing_value is not None
        requested_quantity = sizing_value
        quantity = min(sizing_value, affordable_quantity)
        reason = "FIXED_QUANTITY"

    if quantity < 1:
        return PositionSizingResult(
            final_action=FinalAction.HOLD,
            requested_quantity=requested_quantity,
            final_quantity=None,
            sizing_reason="POSITION_SIZE_BELOW_ONE_SHARE",
        )

    return PositionSizingResult(
        final_action=FinalAction.BUY,
        requested_quantity=requested_quantity,
        final_quantity=quantity,
        sizing_reason=reason,
    )
