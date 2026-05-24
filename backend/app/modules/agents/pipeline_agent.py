from collections.abc import Callable
from decimal import Decimal

from app.domain.enums import AgentStepName, ParsingStatus, TradeAction
from app.modules.agents.fake_pipeline_provider import FakePipelineProvider
from app.modules.agents.output_parser import AgentOutputParseError
from app.modules.agents.pipeline_output_parser import PipelineOutputParser
from app.modules.agents.pipeline_prompt_builder import PipelinePromptBuilder
from app.modules.agents.pipeline_types import (
    MarketAnalysisOutput,
    MarketBias,
    PipelineProvider,
    PipelineStageResult,
    RiskManagerOutput,
    RiskManagerVerdict,
)
from app.modules.agents.types import (
    AgentContext,
    AgentDecision,
    AgentDecisionLogPayload,
    AgentProviderResponse,
    AgentRunResult,
    ParsedAgentOutput,
)


def _base_stage_input(context: AgentContext, stage: AgentStepName) -> dict:
    return {
        "experimentId": context.experiment_id,
        "executionStepId": context.execution_step_id,
        "symbol": context.symbol,
        "stage": stage.value,
    }


class AgentDecisionPipeline:
    agent_name = "AgentDecisionPipeline"

    def __init__(
        self,
        provider: PipelineProvider | None = None,
        prompt_builder: PipelinePromptBuilder | None = None,
        output_parser: PipelineOutputParser | None = None,
    ) -> None:
        self.provider = provider or FakePipelineProvider()
        self.prompt_builder = prompt_builder or PipelinePromptBuilder()
        self.output_parser = output_parser or PipelineOutputParser()

    def run(self, context: AgentContext) -> AgentRunResult:
        input_json = self.prompt_builder.build_input(context)
        market_stage = self._run_market_analyst(context, input_json)
        market_analysis = market_stage.parsed_output
        assert isinstance(market_analysis, MarketAnalysisOutput)

        decision_stage = self._run_trading_decision(
            context, input_json, market_analysis
        )
        proposed_decision = decision_stage.parsed_output
        assert isinstance(proposed_decision, ParsedAgentOutput)

        risk_stage = self._run_risk_manager(
            context, input_json, market_analysis, proposed_decision
        )
        risk_manager = risk_stage.parsed_output
        assert isinstance(risk_manager, RiskManagerOutput)

        final_decision, final_json = self._select_final_decision(
            context=context,
            market_stage=market_stage,
            decision_stage=decision_stage,
            risk_stage=risk_stage,
            proposed_decision=proposed_decision,
            risk_manager=risk_manager,
        )
        log_payloads = (
            self._to_log_payload(context, market_stage),
            self._to_log_payload(context, decision_stage),
            self._to_log_payload(context, risk_stage),
        )
        decision = AgentDecision(
            action=final_decision.action,
            symbol=context.symbol,
            confidence=final_decision.confidence,
            reason=final_decision.rationale,
            raw_decision_json={
                "agent": self.agent_name,
                "promptVersion": self.prompt_builder.prompt_version,
                **final_json,
            },
        )
        return AgentRunResult(
            decision=decision,
            log_payload=log_payloads[-1],
            log_payloads=log_payloads,
        )

    def _run_market_analyst(
        self, context: AgentContext, input_json: dict
    ) -> PipelineStageResult:
        prompt = self.prompt_builder.build_market_analyst_prompt(input_json)
        response = self.provider.complete_market_analyst(prompt, context)
        return self._parse_with_repair(
            step_name=AgentStepName.MARKET_ANALYST,
            stage_label="MarketAnalystAgent",
            input_json={
                **_base_stage_input(context, AgentStepName.MARKET_ANALYST),
                "context": input_json,
            },
            prompt=prompt,
            response=response,
            context=context,
            parser=self.output_parser.parse_market_analysis,
            repair=lambda repair_prompt, raw, error: self.provider.repair_market_analyst(
                repair_prompt, context, raw, error
            ),
            fallback=self._fallback_market_analysis,
            serializer=self.prompt_builder.market_analysis_json,
        )

    def _run_trading_decision(
        self,
        context: AgentContext,
        input_json: dict,
        market_analysis: MarketAnalysisOutput,
    ) -> PipelineStageResult:
        prompt = self.prompt_builder.build_trading_decision_prompt(
            input_json, market_analysis
        )
        response = self.provider.complete_trading_decision(
            prompt, context, market_analysis
        )
        return self._parse_with_repair(
            step_name=AgentStepName.TRADING_DECISION,
            stage_label="TradingDecisionAgent",
            input_json={
                **_base_stage_input(context, AgentStepName.TRADING_DECISION),
                "context": input_json,
                "marketAnalysis": self.prompt_builder.market_analysis_json(
                    market_analysis
                ),
            },
            prompt=prompt,
            response=response,
            context=context,
            parser=self.output_parser.parse_trading_decision,
            repair=lambda repair_prompt, raw, error: self.provider.repair_trading_decision(
                repair_prompt, context, raw, error
            ),
            fallback=lambda reason: self._fallback_decision(reason),
            serializer=self.prompt_builder.trading_decision_json,
        )

    def _run_risk_manager(
        self,
        context: AgentContext,
        input_json: dict,
        market_analysis: MarketAnalysisOutput,
        proposed_decision: ParsedAgentOutput,
    ) -> PipelineStageResult:
        prompt = self.prompt_builder.build_risk_manager_prompt(
            input_json, market_analysis, proposed_decision
        )
        response = self.provider.complete_risk_manager(
            prompt, context, market_analysis, proposed_decision
        )
        return self._parse_with_repair(
            step_name=AgentStepName.RISK_MANAGER,
            stage_label="AgentRiskManager",
            input_json={
                **_base_stage_input(context, AgentStepName.RISK_MANAGER),
                "context": input_json,
                "marketAnalysis": self.prompt_builder.market_analysis_json(
                    market_analysis
                ),
                "proposedDecision": self.prompt_builder.trading_decision_json(
                    proposed_decision
                ),
            },
            prompt=prompt,
            response=response,
            context=context,
            parser=self.output_parser.parse_risk_manager,
            repair=lambda repair_prompt, raw, error: self.provider.repair_risk_manager(
                repair_prompt, context, raw, error
            ),
            fallback=self._fallback_risk_manager,
            serializer=self._risk_manager_json,
        )

    def _parse_with_repair(
        self,
        *,
        step_name: AgentStepName,
        stage_label: str,
        input_json: dict,
        prompt: str,
        response: AgentProviderResponse,
        context: AgentContext,
        parser: Callable[[str], object],
        repair: Callable[[str, str, str], AgentProviderResponse | None],
        fallback: Callable[[str], object],
        serializer: Callable[[object], dict],
    ) -> PipelineStageResult:
        repair_prompt: str | None = None
        repair_raw: str | None = None
        parse_error: str | None = None
        parsing_failed = False
        try:
            parsed = parser(response.raw_output_text)
        except AgentOutputParseError as exc:
            parse_error = str(exc)
            repair_prompt = self.prompt_builder.build_stage_repair_prompt(
                stage_label, response.raw_output_text, parse_error
            )
            repair_response = repair(
                repair_prompt,
                response.raw_output_text,
                parse_error,
            )
            if repair_response is not None:
                repair_raw = repair_response.raw_output_text
                try:
                    parsed = parser(repair_raw)
                except AgentOutputParseError as repair_exc:
                    parse_error = str(repair_exc)
                    parsed = fallback(parse_error)
                    parsing_failed = True
            else:
                parsed = fallback(parse_error)
                parsing_failed = True

        parsed_json = serializer(parsed)
        parsed_json["parseError"] = parse_error
        parsed_json["fallbackUsed"] = parsing_failed
        parsed_json["stage"] = step_name.value
        parsed_json["modelName"] = response.model_name
        parsed_json["modelVersion"] = response.model_version
        _ = context
        return PipelineStageResult(
            step_name=step_name,
            input_json=input_json,
            prompt_text=prompt,
            parsed_output=parsed,
            raw_output_text=response.raw_output_text,
            parsed_output_json=parsed_json,
            parsing_failed=parsing_failed,
            parse_error=parse_error,
            repair_prompt_text=repair_prompt,
            repair_raw_output_text=repair_raw,
        )

    def _select_final_decision(
        self,
        *,
        context: AgentContext,
        market_stage: PipelineStageResult,
        decision_stage: PipelineStageResult,
        risk_stage: PipelineStageResult,
        proposed_decision: ParsedAgentOutput,
        risk_manager: RiskManagerOutput,
    ) -> tuple[ParsedAgentOutput, dict]:
        any_stage_failed = (
            market_stage.parsing_failed
            or decision_stage.parsing_failed
            or risk_stage.parsing_failed
        )
        fallback_reason: str | None = None
        if any_stage_failed:
            final_decision = self._fallback_decision(
                "At least one pipeline stage failed parse and repair."
            )
            fallback_reason = "PIPELINE_STAGE_PARSE_FAILED"
        elif proposed_decision.action is TradeAction.HOLD:
            final_decision = proposed_decision
        elif risk_manager.verdict is RiskManagerVerdict.REJECT:
            final_decision = ParsedAgentOutput(
                action=TradeAction.HOLD,
                confidence=Decimal("0.0000"),
                rationale=f"Agent risk manager rejected proposal: {risk_manager.rationale}",
            )
            fallback_reason = "AGENT_RISK_MANAGER_REJECTED"
        else:
            final_decision = proposed_decision

        threshold_applied = False
        if (
            context.confidence_threshold is not None
            and final_decision.action is not TradeAction.HOLD
            and final_decision.confidence < context.confidence_threshold
        ):
            threshold_applied = True
            final_decision = ParsedAgentOutput(
                action=TradeAction.HOLD,
                confidence=final_decision.confidence,
                rationale=(
                    f"Pipeline confidence {final_decision.confidence} is below "
                    f"configured threshold {context.confidence_threshold}; converted "
                    "to HOLD before RiskCheck."
                ),
            )
            fallback_reason = "CONFIDENCE_BELOW_THRESHOLD"

        final_json = {
            "pipeline": self.agent_name,
            "action": final_decision.action.value,
            "confidence": float(final_decision.confidence),
            "rationale": final_decision.rationale,
            "fallbackUsed": fallback_reason is not None,
            "fallbackReason": fallback_reason,
            "confidenceThresholdApplied": threshold_applied,
            "agentRiskManagerVerdict": risk_manager.verdict.value,
            "agentRiskManagerConfidence": float(risk_manager.confidence),
        }
        return final_decision, final_json

    def _to_log_payload(
        self, context: AgentContext, stage_result: PipelineStageResult
    ) -> AgentDecisionLogPayload:
        status = ParsingStatus.FAILED if stage_result.parsing_failed else ParsingStatus.SUCCESS
        if (
            stage_result.repair_prompt_text is not None
            and not stage_result.parsing_failed
        ):
            status = ParsingStatus.REPAIRED
        return AgentDecisionLogPayload(
            agent_step_name=stage_result.step_name,
            agent_name=self.agent_name,
            prompt_version=self.prompt_builder.prompt_version,
            model_name=stage_result.parsed_output_json.get("modelName"),
            model_version=stage_result.parsed_output_json.get("modelVersion"),
            input_json=stage_result.input_json,
            prompt_text=stage_result.prompt_text,
            raw_output_text=stage_result.raw_output_text,
            parsed_output_json=stage_result.parsed_output_json,
            parsing_status=status,
            repair_prompt_text=stage_result.repair_prompt_text,
            repair_raw_output_text=stage_result.repair_raw_output_text,
        )

    def _fallback_market_analysis(self, reason: str) -> MarketAnalysisOutput:
        return MarketAnalysisOutput(
            market_bias=MarketBias.NEUTRAL,
            confidence=Decimal("0.0000"),
            rationale=f"Market analysis fallback used. {reason}",
        )

    def _fallback_decision(self, reason: str) -> ParsedAgentOutput:
        return ParsedAgentOutput(
            action=TradeAction.HOLD,
            confidence=Decimal("0.0000"),
            rationale=f"Pipeline fallback HOLD used. {reason}",
        )

    def _fallback_risk_manager(self, reason: str) -> RiskManagerOutput:
        return RiskManagerOutput(
            verdict=RiskManagerVerdict.REJECT,
            confidence=Decimal("0.0000"),
            rationale=f"Agent risk manager fallback reject used. {reason}",
        )

    def _risk_manager_json(self, output: object) -> dict:
        assert isinstance(output, RiskManagerOutput)
        return {
            "verdict": output.verdict.value,
            "confidence": float(output.confidence),
            "rationale": output.rationale,
        }
