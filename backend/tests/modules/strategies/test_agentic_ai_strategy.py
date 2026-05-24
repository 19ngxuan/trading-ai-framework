from datetime import date
from decimal import Decimal

from app.domain.enums import AgentMode, TradeAction
from app.modules.agents.types import AgentContext
from app.modules.market_data.provider import DailyBar
from app.modules.strategies.agentic_ai_strategy import AgenticAIStrategy


def test_agentic_ai_strategy_returns_agent_decision_without_side_effects() -> None:
    context = AgentContext(
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
            raw={},
        ),
        cash=Decimal("10000"),
        position_quantity=Decimal("0"),
        current_portfolio_value=Decimal("10000"),
        confidence_threshold=None,
        parameters_json={
            "fakeAgent": {
                "output": {
                    "action": "SELL",
                    "confidence": 0.9,
                    "rationale": "Deterministic sell.",
                }
            }
        },
        agent_mode=AgentMode.SINGLE_AGENT,
        model_name=None,
    )

    result = AgenticAIStrategy().decide(context)

    assert result.decision.action is TradeAction.SELL
    assert result.decision.symbol == "SPY"
    assert result.log_payload.input_json["symbol"] == "SPY"
