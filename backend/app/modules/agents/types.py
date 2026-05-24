from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from app.domain.enums import AgentMode, ParsingStatus, TradeAction
from app.modules.market_data.provider import DailyBar


@dataclass(frozen=True)
class AgentContext:
    experiment_id: int
    execution_step_id: int
    symbol: str
    bar: DailyBar
    cash: Decimal
    position_quantity: Decimal | None
    current_portfolio_value: Decimal | None
    confidence_threshold: Decimal | None
    parameters_json: dict[str, Any] | None
    agent_mode: AgentMode
    model_name: str | None


@dataclass(frozen=True)
class AgentProviderResponse:
    raw_output_text: str
    model_name: str
    model_version: str | None = None


class AgentProvider(Protocol):
    def complete(self, prompt: str, context: AgentContext) -> AgentProviderResponse:
        ...

    def repair(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        ...


@dataclass(frozen=True)
class ParsedAgentOutput:
    action: TradeAction
    confidence: Decimal
    rationale: str


@dataclass(frozen=True)
class AgentDecision:
    action: TradeAction
    symbol: str
    confidence: Decimal
    reason: str
    raw_decision_json: dict[str, Any]


@dataclass(frozen=True)
class AgentDecisionLogPayload:
    agent_name: str
    prompt_version: str
    model_name: str | None
    model_version: str | None
    input_json: dict[str, Any]
    prompt_text: str
    raw_output_text: str
    parsed_output_json: dict[str, Any]
    parsing_status: ParsingStatus
    repair_prompt_text: str | None
    repair_raw_output_text: str | None


@dataclass(frozen=True)
class AgentRunResult:
    decision: AgentDecision
    log_payload: AgentDecisionLogPayload
