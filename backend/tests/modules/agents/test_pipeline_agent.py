from datetime import date
from decimal import Decimal

from app.domain.enums import AgentMode, AgentStepName, ParsingStatus, TradeAction
from app.modules.agents.fake_pipeline_provider import FakePipelineProvider
from app.modules.agents.pipeline_agent import AgentDecisionPipeline
from app.modules.agents.types import AgentContext
from app.modules.market_data.provider import DailyBar


class FundamentalRaisesProvider(FakePipelineProvider):
    def complete_fundamental_analyst(self, prompt: str, context: AgentContext, research):
        raise RuntimeError("fundamental failed")


class PortfolioRepairRaisesProvider(FakePipelineProvider):
    def repair_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ):
        raise RuntimeError("portfolio repair failed")


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
        agent_mode=AgentMode.PIPELINE,
        model_name=None,
    )


def _multi_agent_outputs(
    action: str = "BUY",
    confidence: float = 0.8,
) -> dict:
    return {
        "fakeMultiAgent": {
            "fundamentalAnalystOutput": {
                "signal": "BULLISH",
                "confidence": 0.8,
                "summary": "Healthy fundamentals.",
            },
            "sentimentAnalystOutput": {
                "signal": "BULLISH",
                "confidence": 0.7,
                "summary": "Constructive sentiment.",
            },
            "riskAssessmentOutput": {
                "riskLevel": "MEDIUM",
                "confidence": 0.9,
                "summary": "Risk remains manageable.",
            },
            "portfolioManagerOutput": {
                "action": action,
                "confidence": confidence,
                "rationale": "Multi-agent portfolio manager is constructive.",
            },
        }
    }


def test_multi_agent_buy_returns_six_logs() -> None:
    result = AgentDecisionPipeline().run(_context(_multi_agent_outputs()))

    assert result.decision.action is TradeAction.BUY
    assert len(result.log_payloads) == 6
    assert [payload.agent_step_name for payload in result.log_payloads] == [
        AgentStepName.FETCH_DATA,
        AgentStepName.TECHNICAL_ANALYST,
        AgentStepName.FUNDAMENTAL_ANALYST,
        AgentStepName.SENTIMENT_ANALYST,
        AgentStepName.RISK_MANAGER,
        AgentStepName.PORTFOLIO_MANAGER,
    ]
    assert result.log_payloads[0].parsing_status is ParsingStatus.SUCCESS


def test_multi_agent_low_confidence_returns_hold() -> None:
    result = AgentDecisionPipeline().run(
        _context(_multi_agent_outputs(confidence=0.2), Decimal("0.7000"))
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "CONFIDENCE_BELOW_THRESHOLD"
    )
    assert result.decision.raw_decision_json["originalAction"] == "BUY"
    assert result.decision.raw_decision_json["finalAction"] == "HOLD"


def test_multi_agent_defaults_to_hold_when_no_fake_outputs_exist() -> None:
    result = AgentDecisionPipeline().run(_context(None))

    assert result.decision.action is TradeAction.HOLD
    assert len(result.log_payloads) == 6


def test_multi_agent_stage_provider_exception_uses_fallback_stage() -> None:
    result = AgentDecisionPipeline(provider=FundamentalRaisesProvider()).run(
        _context(_multi_agent_outputs())
    )

    assert result.decision.action is TradeAction.BUY
    assert result.log_payloads[2].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[2].parsed_output_json["fallbackReason"] == (
        "PROVIDER_COMPLETE_EXCEPTION"
    )
    assert result.decision.raw_decision_json["degradedStages"] == [
        AgentStepName.FUNDAMENTAL_ANALYST.value
    ]


def test_multi_agent_portfolio_repair_exception_falls_back_to_hold() -> None:
    result = AgentDecisionPipeline(provider=PortfolioRepairRaisesProvider()).run(
        _context(
            {
                "fakeMultiAgent": {
                    "fundamentalAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.8,
                        "summary": "Healthy fundamentals.",
                    },
                    "sentimentAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.7,
                        "summary": "Constructive sentiment.",
                    },
                    "riskAssessmentOutput": {
                        "riskLevel": "LOW",
                        "confidence": 0.9,
                        "summary": "Low operational risk.",
                    },
                    "portfolioManagerOutput": "not json",
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.log_payloads[-1].parsing_status is ParsingStatus.FAILED
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "PORTFOLIO_MANAGER_STAGE_FAILED"
    )
