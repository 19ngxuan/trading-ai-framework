from typing import Any

from app.modules.agents.pipeline_types import MarketAnalysisOutput
from app.modules.agents.prompt_builder import PromptBuilder
from app.modules.agents.types import ParsedAgentOutput


PIPELINE_PROMPT_VERSION = "agent-pipeline-v1"


class PipelinePromptBuilder(PromptBuilder):
    prompt_version = PIPELINE_PROMPT_VERSION

    def build_market_analyst_prompt(self, input_json: dict[str, Any]) -> str:
        return self._guarded_prompt(
            "MarketAnalystAgent",
            "Return strict JSON with marketBias BULLISH, BEARISH, or NEUTRAL, confidence, and rationale.",
            input_json,
        )

    def build_trading_decision_prompt(
        self,
        input_json: dict[str, Any],
        market_analysis: MarketAnalysisOutput,
    ) -> str:
        enriched = {
            **input_json,
            "marketAnalysis": self.market_analysis_json(market_analysis),
        }
        return self._guarded_prompt(
            "TradingDecisionAgent",
            "Return strict JSON with action BUY, SELL, or HOLD, confidence, and rationale.",
            enriched,
        )

    def build_risk_manager_prompt(
        self,
        input_json: dict[str, Any],
        market_analysis: MarketAnalysisOutput,
        proposed_decision: ParsedAgentOutput,
    ) -> str:
        enriched = {
            **input_json,
            "marketAnalysis": self.market_analysis_json(market_analysis),
            "proposedDecision": self.trading_decision_json(proposed_decision),
        }
        return self._guarded_prompt(
            "AgentRiskManager",
            "Return strict JSON with verdict APPROVE or REJECT, confidence, and rationale.",
            enriched,
        )

    def build_stage_repair_prompt(
        self, stage_name: str, raw_output_text: str, error_message: str
    ) -> str:
        return (
            f"Repair {stage_name} output into strict valid JSON for that stage. "
            f"Parse error: {error_message}. Previous output: {raw_output_text}"
        )

    def market_analysis_json(self, output: MarketAnalysisOutput) -> dict[str, Any]:
        return {
            "marketBias": output.market_bias.value,
            "confidence": float(output.confidence),
            "rationale": output.rationale,
        }

    def trading_decision_json(self, output: ParsedAgentOutput) -> dict[str, Any]:
        return {
            "action": output.action.value,
            "confidence": float(output.confidence),
            "rationale": output.rationale,
        }

    def _guarded_prompt(
        self, stage_name: str, instruction: str, input_json: dict[str, Any]
    ) -> str:
        return (
            f"{stage_name} is a deterministic advisory stage for a controlled "
            "trading workflow. It must not call tools, broker, Alpaca, order, "
            "trade, portfolio, scheduler, repository, persistence, or market-data "
            "APIs. RiskCheck remains mandatory and authoritative after the final "
            f"pipeline decision. {instruction} Input: {input_json}"
        )
