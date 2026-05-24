from datetime import date
from decimal import Decimal

from app.domain.enums import AgentMode, ParsingStatus, TradeAction
from app.modules.agents.single_agent import SingleAgent
from app.modules.agents.types import AgentContext
from app.modules.market_data.provider import DailyBar


def _context(
    parameters_json: dict | None,
    confidence_threshold: Decimal | None = None,
) -> AgentContext:
    return AgentContext(
        experiment_id=1,
        execution_step_id=1,
        symbol="SPY",
        bar=DailyBar(
            date=date(2024, 1, 2),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            adjusted_close=Decimal("100"),
            volume=Decimal("1000000"),
            raw={"date": "2024-01-02"},
        ),
        cash=Decimal("10000"),
        position_quantity=Decimal("0"),
        current_portfolio_value=Decimal("10000"),
        confidence_threshold=confidence_threshold,
        parameters_json=parameters_json,
        agent_mode=AgentMode.SINGLE_AGENT,
        model_name=None,
    )


def test_single_agent_uses_valid_fake_output() -> None:
    result = SingleAgent().run(
        _context(
            {
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.8,
                        "rationale": "Deterministic buy.",
                    }
                }
            }
        )
    )

    assert result.decision.action is TradeAction.BUY
    assert result.decision.confidence == Decimal("0.8000")
    assert result.log_payload.parsing_status is ParsingStatus.SUCCESS
    assert result.log_payload.repair_prompt_text is None


def test_single_agent_repairs_invalid_output() -> None:
    result = SingleAgent().run(
        _context(
            {
                "fakeAgent": {
                    "output": "not json",
                    "repairOutput": {
                        "action": "HOLD",
                        "confidence": 0.4,
                        "rationale": "Repaired hold.",
                    },
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.log_payload.parsing_status is ParsingStatus.REPAIRED
    assert result.log_payload.repair_prompt_text is not None
    assert result.log_payload.repair_raw_output_text is not None


def test_single_agent_falls_back_to_hold_when_repair_fails() -> None:
    result = SingleAgent().run(
        _context(
            {
                "fakeAgent": {
                    "output": "not json",
                    "repairOutput": "still not json",
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.confidence == Decimal("0.0000")
    assert result.log_payload.parsing_status is ParsingStatus.FAILED
    assert result.log_payload.parsed_output_json["fallbackUsed"] is True


def test_single_agent_low_confidence_converts_to_hold() -> None:
    result = SingleAgent().run(
        _context(
            {
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.2,
                        "rationale": "Weak buy.",
                    }
                }
            },
            confidence_threshold=Decimal("0.7000"),
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.confidence == Decimal("0.2000")
    assert result.log_payload.parsed_output_json["confidenceThresholdApplied"] is True
