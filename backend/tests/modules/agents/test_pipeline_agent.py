from datetime import date
from decimal import Decimal

from app.domain.enums import AgentMode, AgentStepName, ParsingStatus, TradeAction
from app.modules.agents.fake_pipeline_provider import FakePipelineProvider
from app.modules.agents.pipeline_agent import AgentDecisionPipeline
from app.modules.agents.types import AgentContext
from app.modules.market_data.provider import DailyBar


class MarketAnalystRaisesProvider(FakePipelineProvider):
    def complete_market_analyst(self, prompt: str, context: AgentContext):
        raise RuntimeError("market analyst failed")


class TradingDecisionRaisesProvider(FakePipelineProvider):
    def complete_trading_decision(self, prompt, context, market_analysis):
        raise RuntimeError("trading decision failed")


class RiskManagerRaisesProvider(FakePipelineProvider):
    def complete_risk_manager(
        self, prompt, context, market_analysis, proposed_decision
    ):
        raise RuntimeError("risk manager failed")


class TradingDecisionRepairRaisesProvider(FakePipelineProvider):
    def repair_trading_decision(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ):
        raise RuntimeError("trading decision repair failed")


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


def _pipeline_outputs(
    action: str = "BUY",
    verdict: str = "APPROVE",
    confidence: float = 0.8,
) -> dict:
    return {
        "fakePipeline": {
            "marketAnalystOutput": {
                "marketBias": "BULLISH",
                "confidence": 0.8,
                "rationale": "Bullish context.",
            },
            "tradingDecisionOutput": {
                "action": action,
                "confidence": confidence,
                "rationale": "Pipeline proposal.",
            },
            "riskManagerOutput": {
                "verdict": verdict,
                "confidence": 0.9,
                "rationale": "Agent-level verdict.",
            },
        }
    }


def test_pipeline_buy_approved_returns_buy_and_three_logs() -> None:
    result = AgentDecisionPipeline().run(_context(_pipeline_outputs()))

    assert result.decision.action is TradeAction.BUY
    assert len(result.log_payloads) == 3
    assert [payload.agent_step_name for payload in result.log_payloads] == [
        AgentStepName.MARKET_ANALYST,
        AgentStepName.TRADING_DECISION,
        AgentStepName.RISK_MANAGER,
    ]
    assert all(
        payload.parsing_status is ParsingStatus.SUCCESS
        for payload in result.log_payloads
    )


def test_pipeline_rejected_proposal_returns_hold() -> None:
    result = AgentDecisionPipeline().run(
        _context(_pipeline_outputs(action="BUY", verdict="REJECT"))
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.confidence == Decimal("0.0000")
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "AGENT_RISK_MANAGER_REJECTED"
    )
    assert result.decision.raw_decision_json["originalAction"] == "BUY"
    assert result.decision.raw_decision_json["finalAction"] == "HOLD"
    assert len(result.decision.raw_decision_json["pipelineStageSummary"]) == 3


def test_pipeline_failed_repair_returns_hold() -> None:
    result = AgentDecisionPipeline().run(
        _context(
            {
                "fakePipeline": {
                    "marketAnalystOutput": {
                        "marketBias": "NEUTRAL",
                        "confidence": 0.5,
                        "rationale": "Neutral.",
                    },
                    "tradingDecisionOutput": "not json",
                    "tradingDecisionRepairOutput": "still not json",
                    "riskManagerOutput": {
                        "verdict": "APPROVE",
                        "confidence": 0.9,
                        "rationale": "Approved.",
                    },
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.confidence == Decimal("0.0000")
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "PIPELINE_STAGE_PARSE_FAILED"
    )
    assert result.log_payloads[1].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[1].parsed_output_json["fallbackReason"] == (
        "REPAIR_PARSE_FAILED"
    )
    assert result.log_payloads[1].parsed_output_json["pipelineStage"] == (
        AgentStepName.TRADING_DECISION.value
    )


def test_pipeline_invalid_output_repairs() -> None:
    result = AgentDecisionPipeline().run(
        _context(
            {
                "fakePipeline": {
                    "marketAnalystOutput": "not json",
                    "marketAnalystRepairOutput": {
                        "marketBias": "NEUTRAL",
                        "confidence": 0.4,
                        "rationale": "Repaired.",
                    },
                    "tradingDecisionOutput": {
                        "action": "HOLD",
                        "confidence": 0.4,
                        "rationale": "Hold.",
                    },
                    "riskManagerOutput": {
                        "verdict": "APPROVE",
                        "confidence": 0.9,
                        "rationale": "Approved.",
                    },
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.log_payloads[0].parsing_status is ParsingStatus.REPAIRED
    assert result.log_payloads[0].repair_prompt_text is not None


def test_pipeline_low_confidence_returns_hold() -> None:
    result = AgentDecisionPipeline().run(
        _context(_pipeline_outputs(confidence=0.2), Decimal("0.7000"))
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "CONFIDENCE_BELOW_THRESHOLD"
    )
    assert result.decision.raw_decision_json["originalAction"] == "BUY"
    assert result.decision.raw_decision_json["originalConfidence"] == 0.2
    assert result.decision.raw_decision_json["finalAction"] == "HOLD"


def test_pipeline_default_output_is_hold() -> None:
    result = AgentDecisionPipeline().run(_context(None))

    assert result.decision.action is TradeAction.HOLD
    assert len(result.log_payloads) == 3


def test_pipeline_market_analyst_provider_exception_falls_back_to_hold() -> None:
    result = AgentDecisionPipeline(provider=MarketAnalystRaisesProvider()).run(
        _context(_pipeline_outputs())
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "PIPELINE_STAGE_PARSE_FAILED"
    )
    assert result.log_payloads[0].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[0].parsed_output_json["fallbackReason"] == (
        "PROVIDER_COMPLETE_EXCEPTION"
    )
    assert result.log_payloads[0].parsed_output_json["parseError"] == (
        "market analyst failed"
    )


def test_pipeline_trading_decision_provider_exception_falls_back_to_hold() -> None:
    result = AgentDecisionPipeline(provider=TradingDecisionRaisesProvider()).run(
        _context(_pipeline_outputs())
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.log_payloads[1].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[1].parsed_output_json["fallbackReason"] == (
        "PROVIDER_COMPLETE_EXCEPTION"
    )
    assert result.log_payloads[1].parsed_output_json["finalAction"] == "HOLD"


def test_pipeline_risk_manager_provider_exception_falls_back_to_hold() -> None:
    result = AgentDecisionPipeline(provider=RiskManagerRaisesProvider()).run(
        _context(_pipeline_outputs())
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.log_payloads[2].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[2].parsed_output_json["fallbackReason"] == (
        "PROVIDER_COMPLETE_EXCEPTION"
    )


def test_pipeline_repair_provider_exception_falls_back_to_hold() -> None:
    result = AgentDecisionPipeline(provider=TradingDecisionRepairRaisesProvider()).run(
        _context(
            {
                "fakePipeline": {
                    "marketAnalystOutput": {
                        "marketBias": "NEUTRAL",
                        "confidence": 0.5,
                        "rationale": "Neutral.",
                    },
                    "tradingDecisionOutput": "not json",
                    "riskManagerOutput": {
                        "verdict": "APPROVE",
                        "confidence": 0.9,
                        "rationale": "Approved.",
                    },
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.log_payloads[1].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[1].repair_prompt_text is not None
    assert result.log_payloads[1].parsed_output_json["fallbackReason"] == (
        "PROVIDER_REPAIR_EXCEPTION"
    )
