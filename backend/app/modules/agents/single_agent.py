from decimal import Decimal

from app.domain.enums import AgentStepName, ParsingStatus, TradeAction
from app.modules.agents.fake_provider import FakeAgentProvider
from app.modules.agents.output_parser import AgentOutputParseError, AgentOutputParser
from app.modules.agents.prompt_builder import PromptBuilder
from app.modules.agents.types import (
    AgentContext,
    AgentDecision,
    AgentDecisionLogPayload,
    AgentProviderResponse,
    AgentProvider,
    AgentRunResult,
    ParsedAgentOutput,
)


class SingleAgent:
    agent_name = "SingleAgent"

    def __init__(
        self,
        provider: AgentProvider | None = None,
        prompt_builder: PromptBuilder | None = None,
        output_parser: AgentOutputParser | None = None,
    ) -> None:
        self.provider = provider or FakeAgentProvider()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.output_parser = output_parser or AgentOutputParser()

    def run(self, context: AgentContext) -> AgentRunResult:
        input_json = self.prompt_builder.build_input(context)
        prompt = self.prompt_builder.build_prompt(input_json)

        repair_prompt: str | None = None
        repair_raw_output: str | None = None
        parsing_status = ParsingStatus.SUCCESS
        fallback_used = False
        fallback_reason: str | None = None
        parse_error: str | None = None

        try:
            response = self.provider.complete(prompt, context)
        except Exception as exc:
            parse_error = str(exc)
            parsed = self._fallback_output(parse_error)
            response = self._failed_provider_response(context)
            parsing_status = ParsingStatus.FAILED
            fallback_used = True
            fallback_reason = "PROVIDER_COMPLETE_EXCEPTION"
        else:
            try:
                parsed = self.output_parser.parse(response.raw_output_text)
            except AgentOutputParseError as exc:
                parse_error = str(exc)
                repair_prompt = self.prompt_builder.build_repair_prompt(
                    response.raw_output_text, parse_error
                )
                try:
                    repair_response = self.provider.repair(
                        repair_prompt,
                        context,
                        response.raw_output_text,
                        parse_error,
                    )
                except Exception as repair_exc:
                    parse_error = str(repair_exc)
                    parsed = self._fallback_output(parse_error)
                    parsing_status = ParsingStatus.FAILED
                    fallback_used = True
                    fallback_reason = "PROVIDER_REPAIR_EXCEPTION"
                else:
                    if repair_response is not None:
                        repair_raw_output = repair_response.raw_output_text
                        try:
                            parsed = self.output_parser.parse(repair_raw_output)
                            parsing_status = ParsingStatus.REPAIRED
                        except AgentOutputParseError as repair_parse_exc:
                            parse_error = str(repair_parse_exc)
                            parsed = self._fallback_output(parse_error)
                            parsing_status = ParsingStatus.FAILED
                            fallback_used = True
                            fallback_reason = "REPAIR_PARSE_FAILED"
                    else:
                        parsed = self._fallback_output(parse_error)
                        parsing_status = ParsingStatus.FAILED
                        fallback_used = True
                        fallback_reason = "REPAIR_UNAVAILABLE"

        original_action = parsed.action
        original_confidence = parsed.confidence
        final_parsed, threshold_applied = self._apply_confidence_threshold(
            parsed, context.confidence_threshold
        )
        if threshold_applied:
            fallback_used = True
            fallback_reason = "CONFIDENCE_BELOW_THRESHOLD"
        decision_json = {
            "action": final_parsed.action.value,
            "confidence": float(final_parsed.confidence),
            "rationale": final_parsed.rationale,
            "originalAction": original_action.value,
            "originalConfidence": float(original_confidence),
            "finalAction": final_parsed.action.value,
            "parseError": parse_error,
            "fallbackUsed": fallback_used,
            "fallbackReason": fallback_reason,
            "confidenceThresholdApplied": threshold_applied,
        }
        decision = AgentDecision(
            action=final_parsed.action,
            symbol=context.symbol,
            confidence=final_parsed.confidence,
            reason=final_parsed.rationale,
            raw_decision_json={
                "agent": self.agent_name,
                "provider": response.model_name,
                "promptVersion": self.prompt_builder.prompt_version,
                **decision_json,
            },
        )
        log_payload = AgentDecisionLogPayload(
            agent_step_name=AgentStepName.SINGLE_DECISION_AGENT,
            agent_name=self.agent_name,
            prompt_version=self.prompt_builder.prompt_version,
            model_name=response.model_name,
            model_version=response.model_version,
            input_json=input_json,
            prompt_text=prompt,
            raw_output_text=response.raw_output_text,
            parsed_output_json=decision_json,
            parsing_status=parsing_status,
            repair_prompt_text=repair_prompt,
            repair_raw_output_text=repair_raw_output,
        )
        return AgentRunResult(decision=decision, log_payload=log_payload)

    def _failed_provider_response(self, context: AgentContext) -> AgentProviderResponse:
        return AgentProviderResponse(
            raw_output_text="",
            model_name=context.model_name or "deterministic-fake-agent",
            model_version=None,
        )

    def _fallback_output(self, reason: str) -> ParsedAgentOutput:
        return ParsedAgentOutput(
            action=TradeAction.HOLD,
            confidence=Decimal("0.0000"),
            rationale=f"Agent output could not be parsed or repaired; fallback HOLD used. {reason}",
        )

    def _apply_confidence_threshold(
        self,
        parsed: ParsedAgentOutput,
        threshold: Decimal | None,
    ) -> tuple[ParsedAgentOutput, bool]:
        if (
            threshold is None
            or parsed.action is TradeAction.HOLD
            or parsed.confidence >= threshold
        ):
            return parsed, False
        return (
            ParsedAgentOutput(
                action=TradeAction.HOLD,
                confidence=parsed.confidence,
                rationale=(
                    f"Agent confidence {parsed.confidence} is below configured "
                    f"threshold {threshold}; converted to HOLD before RiskCheck."
                ),
            ),
            True,
        )
