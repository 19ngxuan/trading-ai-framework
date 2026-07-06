from decimal import Decimal
from types import SimpleNamespace

from app.domain.enums import FinalAction, TradeAction
from app.modules.execution.risk import BuyAndHoldRiskValidator
from app.persistence.models import PortfolioModel


def _portfolio(
    *,
    cash: Decimal = Decimal("10000"),
    position_quantity: Decimal = Decimal("0"),
    current_portfolio_value: Decimal = Decimal("10000"),
) -> PortfolioModel:
    return PortfolioModel(
        experiment_id=1,
        cash=cash,
        position_symbol="AAPL",
        position_quantity=position_quantity,
        current_price=Decimal("100"),
        current_position_value=position_quantity * Decimal("100"),
        current_portfolio_value=current_portfolio_value,
        updated_at=None,
    )


def _decision(action: TradeAction, target: Decimal):
    return SimpleNamespace(
        action=action,
        symbol="AAPL",
        reason="target exposure",
        target_exposure_pct=target,
    )


def test_target_exposure_buy_uses_delta_not_all_in() -> None:
    result = BuyAndHoldRiskValidator().evaluate_target_exposure(
        _decision(TradeAction.BUY, Decimal("0.2500")),
        _portfolio(),
        Decimal("100"),
    )

    assert result.final_action is FinalAction.BUY
    assert result.final_quantity == Decimal("25")


def test_target_exposure_reduce_long_sells_delta_only() -> None:
    result = BuyAndHoldRiskValidator().evaluate_target_exposure(
        _decision(TradeAction.SELL, Decimal("0.1000")),
        _portfolio(
            cash=Decimal("5000"),
            position_quantity=Decimal("50"),
            current_portfolio_value=Decimal("10000"),
        ),
        Decimal("100"),
    )

    assert result.final_action is FinalAction.SELL
    assert result.final_quantity == Decimal("40")


def test_target_exposure_never_shorts() -> None:
    result = BuyAndHoldRiskValidator().evaluate_target_exposure(
        _decision(TradeAction.SELL, Decimal("0")),
        _portfolio(position_quantity=Decimal("0")),
        Decimal("100"),
    )

    assert result.final_action is FinalAction.HOLD
