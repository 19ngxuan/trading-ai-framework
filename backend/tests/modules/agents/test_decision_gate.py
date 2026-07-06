from datetime import date
from decimal import Decimal

from app.domain.enums import AgentMode, PrimaryDriver, TradeAction, TradeIntent
from app.modules.agents.decision_gate import AgentDecisionGate
from app.modules.agents.types import AgentContext, ParsedAgentOutput
from app.modules.market_data.provider import DailyBar


def _context(
    *,
    position_quantity: Decimal = Decimal("0"),
    confidence_threshold: Decimal = Decimal("0.7000"),
) -> AgentContext:
    return AgentContext(
        experiment_id=1,
        execution_step_id=2,
        symbol="AAPL",
        bar=DailyBar(
            date=date(2026, 1, 2),
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            adjusted_close=Decimal("100"),
            volume=Decimal("1000"),
            raw={},
        ),
        cash=Decimal("9000"),
        position_quantity=position_quantity,
        current_portfolio_value=Decimal("10000"),
        confidence_threshold=confidence_threshold,
        parameters_json=None,
        agent_mode=AgentMode.SINGLE_AGENT,
        model_name="fake",
    )


def _output(**overrides) -> ParsedAgentOutput:
    payload = {
        "action": TradeAction.BUY,
        "trade_intent": TradeIntent.OPEN_LONG,
        "target_exposure_pct": Decimal("0.2500"),
        "confidence": Decimal("0.9000"),
        "primary_driver": PrimaryDriver.TECHNICAL,
        "new_information": True,
        "rationale": "Bullish setup.",
        "event_id": None,
    }
    payload.update(overrides)
    return ParsedAgentOutput(**payload)


def test_buy_without_new_information_becomes_hold() -> None:
    result = AgentDecisionGate().apply(
        _output(new_information=False),
        _context(),
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.audit_json["fallbackReason"] == "BUY_WITHOUT_NEW_INFORMATION"


def test_sell_without_position_becomes_hold() -> None:
    result = AgentDecisionGate().apply(
        _output(
            action=TradeAction.SELL,
            trade_intent=TradeIntent.CLOSE_LONG,
            target_exposure_pct=Decimal("0"),
        ),
        _context(position_quantity=Decimal("0")),
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.audit_json["fallbackReason"] == "SELL_WITHOUT_POSITION"


def test_target_exposure_is_clamped_and_audited() -> None:
    result = AgentDecisionGate().apply(
        _output(target_exposure_pct=Decimal("1.0000")),
        _context(),
        max_exposure_pct=Decimal("0.5000"),
    )

    assert result.decision.target_exposure_pct == Decimal("0.5000")
    assert result.audit_json["targetExposureClamped"] is True
