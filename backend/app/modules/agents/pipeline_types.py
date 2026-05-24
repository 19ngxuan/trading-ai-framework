from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol

from app.domain.enums import AgentStepName
from app.modules.agents.types import AgentContext, AgentProviderResponse


class MarketBias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RiskManagerVerdict(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class MarketAnalysisOutput:
    market_bias: MarketBias
    confidence: Decimal
    rationale: str


@dataclass(frozen=True)
class RiskManagerOutput:
    verdict: RiskManagerVerdict
    confidence: Decimal
    rationale: str


@dataclass(frozen=True)
class PipelineStageResult:
    step_name: AgentStepName
    input_json: dict
    prompt_text: str
    parsed_output: MarketAnalysisOutput | RiskManagerOutput | object
    raw_output_text: str
    parsed_output_json: dict
    parsing_failed: bool
    parse_error: str | None
    repair_prompt_text: str | None
    repair_raw_output_text: str | None


class PipelineProvider(Protocol):
    def complete_market_analyst(
        self, prompt: str, context: AgentContext
    ) -> AgentProviderResponse:
        ...

    def repair_market_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...

    def complete_trading_decision(
        self,
        prompt: str,
        context: AgentContext,
        market_analysis: MarketAnalysisOutput,
    ) -> AgentProviderResponse:
        ...

    def repair_trading_decision(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...

    def complete_risk_manager(
        self,
        prompt: str,
        context: AgentContext,
        market_analysis: MarketAnalysisOutput,
        proposed_decision: object,
    ) -> AgentProviderResponse:
        ...

    def repair_risk_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...
