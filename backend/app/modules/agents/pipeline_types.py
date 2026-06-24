from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol

from app.domain.enums import AgentStepName
from app.modules.agents.research_providers import (
    FundamentalResearchSnapshot,
    SentimentResearchSnapshot,
)
from app.modules.agents.types import AgentContext, AgentProviderResponse, ParsedAgentOutput


class MarketBias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RiskManagerVerdict(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


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
class FetchedDataOutput:
    current_price: Decimal
    history_length: int
    volatility_pct: Decimal | None
    fundamental_data_available: bool
    sentiment_data_available: bool
    rationale: str


@dataclass(frozen=True)
class TechnicalAnalysisOutput:
    signal: MarketBias
    confidence: Decimal
    rationale: str
    rsi: Decimal | None
    sma_20: Decimal | None
    trend: str
    volatility_pct: Decimal | None


@dataclass(frozen=True)
class FundamentalAnalysisOutput:
    signal: MarketBias
    confidence: Decimal
    summary: str


@dataclass(frozen=True)
class SentimentAnalysisOutput:
    signal: MarketBias
    confidence: Decimal
    summary: str


@dataclass(frozen=True)
class RiskAssessmentOutput:
    risk_level: RiskLevel
    confidence: Decimal
    summary: str


@dataclass(frozen=True)
class PipelineStageResult:
    step_name: AgentStepName
    input_json: dict
    prompt_text: str | None
    parsed_output: (
        FetchedDataOutput
        | TechnicalAnalysisOutput
        | FundamentalAnalysisOutput
        | SentimentAnalysisOutput
        | RiskAssessmentOutput
        | MarketAnalysisOutput
        | RiskManagerOutput
        | ParsedAgentOutput
        | object
    )
    raw_output_text: str | None
    parsed_output_json: dict
    parsing_failed: bool
    parse_error: str | None
    fallback_reason: str | None
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
        proposed_decision: ParsedAgentOutput,
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

    def complete_fundamental_analyst(
        self,
        prompt: str,
        context: AgentContext,
        research_snapshot: FundamentalResearchSnapshot,
    ) -> AgentProviderResponse:
        ...

    def repair_fundamental_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...

    def complete_sentiment_analyst(
        self,
        prompt: str,
        context: AgentContext,
        research_snapshot: SentimentResearchSnapshot,
        technical_analysis: TechnicalAnalysisOutput,
    ) -> AgentProviderResponse:
        ...

    def repair_sentiment_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...

    def complete_risk_assessment(
        self,
        prompt: str,
        context: AgentContext,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: FundamentalAnalysisOutput,
        sentiment_analysis: SentimentAnalysisOutput,
    ) -> AgentProviderResponse:
        ...

    def repair_risk_assessment(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...

    def complete_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: FundamentalAnalysisOutput,
        sentiment_analysis: SentimentAnalysisOutput,
        risk_assessment: RiskAssessmentOutput,
    ) -> AgentProviderResponse:
        ...

    def repair_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...
