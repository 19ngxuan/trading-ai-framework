import json
from collections.abc import Callable, Sequence
from datetime import timedelta
from decimal import Decimal

from app.domain.enums import (
    AgentStepName,
    ParsingStatus,
    PrimaryDriver,
    TradeAction,
    TradeIntent,
    TradingFrequency,
)
from app.modules.agents.decision_gate import AgentDecisionGate
from app.modules.agents.fake_pipeline_provider import FakePipelineProvider
from app.modules.agents.output_parser import AgentOutputParseError
from app.modules.agents.pipeline_output_parser import PipelineOutputParser
from app.modules.agents.pipeline_prompt_builder import PipelinePromptBuilder
from app.modules.agents.pipeline_types import (
    FetchedDataOutput,
    FundamentalAnalysisOutput,
    MarketBias,
    PipelineProvider,
    PipelineStageResult,
    RiskAssessmentOutput,
    RiskLevel,
    SentimentAnalysisOutput,
    TechnicalAnalysisOutput,
)
from app.modules.agents.research_providers import (
    FundamentalResearchProvider,
    ParameterFundamentalResearchProvider,
    ParameterSentimentResearchProvider,
    SentimentResearchProvider,
)
from app.modules.agents.types import (
    AgentContext,
    AgentDecision,
    AgentDecisionLogPayload,
    AgentProviderResponse,
    AgentRunResult,
    ParsedAgentOutput,
)
from app.modules.market_data.provider import DailyBar, MarketDataProvider


def _base_stage_input(context: AgentContext, stage: AgentStepName) -> dict:
    return {
        "experimentId": context.experiment_id,
        "executionStepId": context.execution_step_id,
        "symbol": context.symbol,
        "stage": stage.value,
    }


class AgentDecisionPipeline:
    agent_name = "MultiAgentDecisionGraph"

    def __init__(
        self,
        provider: PipelineProvider | None = None,
        prompt_builder: PipelinePromptBuilder | None = None,
        output_parser: PipelineOutputParser | None = None,
        market_data_provider: MarketDataProvider | None = None,
        fundamental_provider: FundamentalResearchProvider | None = None,
        sentiment_provider: SentimentResearchProvider | None = None,
        decision_gate: AgentDecisionGate | None = None,
    ) -> None:
        self.provider = provider or FakePipelineProvider()
        self.prompt_builder = prompt_builder or PipelinePromptBuilder()
        self.output_parser = output_parser or PipelineOutputParser()
        self.market_data_provider = market_data_provider
        self.fundamental_provider = (
            fundamental_provider or ParameterFundamentalResearchProvider()
        )
        self.sentiment_provider = sentiment_provider or ParameterSentimentResearchProvider()
        self.decision_gate = decision_gate or AgentDecisionGate()

    def run(self, context: AgentContext) -> AgentRunResult:
        input_json = self.prompt_builder.build_input(context)
        price_history = self._load_price_history(context)
        fundamental_snapshot = self.fundamental_provider.load(context)
        sentiment_snapshot = self.sentiment_provider.load(context)

        fetch_stage = self._run_fetch_data(
            context,
            input_json,
            price_history,
            fundamental_snapshot,
            sentiment_snapshot,
        )
        fetched_data = fetch_stage.parsed_output
        assert isinstance(fetched_data, FetchedDataOutput)

        technical_stage = self._run_technical_analyst(
            context,
            input_json,
            price_history,
            fetched_data,
        )
        technical_analysis = technical_stage.parsed_output
        assert isinstance(technical_analysis, TechnicalAnalysisOutput)

        fundamental_stage = self._run_fundamental_analyst(
            context,
            input_json,
            fetched_data,
            fundamental_snapshot,
        )
        fundamental_analysis = fundamental_stage.parsed_output
        assert isinstance(fundamental_analysis, FundamentalAnalysisOutput)

        sentiment_stage = self._run_sentiment_analyst(
            context,
            input_json,
            fetched_data,
            sentiment_snapshot,
            technical_analysis,
        )
        sentiment_analysis = sentiment_stage.parsed_output
        assert isinstance(sentiment_analysis, SentimentAnalysisOutput)

        risk_stage = self._run_risk_assessment(
            context,
            input_json,
            technical_analysis,
            fundamental_analysis,
            sentiment_analysis,
        )
        risk_assessment = risk_stage.parsed_output
        assert isinstance(risk_assessment, RiskAssessmentOutput)

        portfolio_stage = self._run_portfolio_manager(
            context,
            input_json,
            technical_analysis,
            fundamental_analysis,
            sentiment_analysis,
            risk_assessment,
        )
        proposed_decision = portfolio_stage.parsed_output
        assert isinstance(proposed_decision, ParsedAgentOutput)

        stage_results = (
            fetch_stage,
            technical_stage,
            fundamental_stage,
            sentiment_stage,
            risk_stage,
            portfolio_stage,
        )
        final_decision, final_json = self._select_final_decision(
            context=context,
            proposed_decision=proposed_decision,
            technical_analysis=technical_analysis,
            fundamental_analysis=fundamental_analysis,
            sentiment_analysis=sentiment_analysis,
            risk_assessment=risk_assessment,
            stage_results=stage_results,
        )
        log_payloads = tuple(
            self._to_log_payload(stage_result) for stage_result in stage_results
        )
        decision = AgentDecision(
            action=final_decision.action,
            symbol=context.symbol,
            confidence=final_decision.confidence,
            reason=final_decision.rationale,
            raw_decision_json={
                "agent": self.agent_name,
                "agentVersion": "MULTI_AGENT_V2_TRADING",
                "promptVersion": self.prompt_builder.prompt_version,
                **final_json,
            },
            trade_intent=final_decision.trade_intent,
            target_exposure_pct=final_decision.target_exposure_pct,
            primary_driver=final_decision.primary_driver,
            new_information=final_decision.new_information,
        )
        return AgentRunResult(
            decision=decision,
            log_payload=log_payloads[-1],
            log_payloads=log_payloads,
        )

    def _run_fetch_data(
        self,
        context: AgentContext,
        input_json: dict,
        price_history: list[DailyBar],
        fundamental_snapshot,
        sentiment_snapshot,
    ) -> PipelineStageResult:
        volatility_pct = self._volatility_pct(price_history)
        output = FetchedDataOutput(
            current_price=context.bar.adjusted_close,
            history_length=len(price_history),
            volatility_pct=volatility_pct,
            fundamental_data_available=bool(
                fundamental_snapshot.raw_data or fundamental_snapshot.notes
            ),
            sentiment_data_available=bool(
                sentiment_snapshot.raw_data
                or sentiment_snapshot.summary
                or sentiment_snapshot.headlines
            ),
            rationale=(
                "Collected framework-managed market data and optional research context "
                "for the multi-agent workflow."
            ),
        )
        stage_input = {
            **_base_stage_input(context, AgentStepName.FETCH_DATA),
            "context": input_json,
        }
        parsed_output_json = self.prompt_builder.fetched_data_json(output)
        parsed_output_json["stage"] = AgentStepName.FETCH_DATA.value
        parsed_output_json["fallbackUsed"] = False
        return PipelineStageResult(
            step_name=AgentStepName.FETCH_DATA,
            input_json=stage_input,
            prompt_text=None,
            parsed_output=output,
            raw_output_text=json.dumps(parsed_output_json, sort_keys=True),
            parsed_output_json=parsed_output_json,
            parsing_failed=False,
            parse_error=None,
            fallback_reason=None,
            repair_prompt_text=None,
            repair_raw_output_text=None,
        )

    def _run_technical_analyst(
        self,
        context: AgentContext,
        input_json: dict,
        price_history: list[DailyBar],
        fetched_data: FetchedDataOutput,
    ) -> PipelineStageResult:
        output = self._technical_analysis(context, price_history, fetched_data)
        stage_input = {
            **_base_stage_input(context, AgentStepName.TECHNICAL_ANALYST),
            "context": input_json,
            "fetchedData": self.prompt_builder.fetched_data_json(fetched_data),
        }
        parsed_output_json = self.prompt_builder.technical_analysis_json(output)
        parsed_output_json["stage"] = AgentStepName.TECHNICAL_ANALYST.value
        parsed_output_json["fallbackUsed"] = False
        return PipelineStageResult(
            step_name=AgentStepName.TECHNICAL_ANALYST,
            input_json=stage_input,
            prompt_text=None,
            parsed_output=output,
            raw_output_text=json.dumps(parsed_output_json, sort_keys=True),
            parsed_output_json=parsed_output_json,
            parsing_failed=False,
            parse_error=None,
            fallback_reason=None,
            repair_prompt_text=None,
            repair_raw_output_text=None,
        )

    def _run_fundamental_analyst(
        self,
        context: AgentContext,
        input_json: dict,
        fetched_data: FetchedDataOutput,
        research_snapshot,
    ) -> PipelineStageResult:
        prompt = self.prompt_builder.build_fundamental_analyst_prompt(
            input_json,
            fetched_data,
            research_snapshot,
        )
        stage_input = {
            **_base_stage_input(context, AgentStepName.FUNDAMENTAL_ANALYST),
            "context": input_json,
            "fetchedData": self.prompt_builder.fetched_data_json(fetched_data),
            "research": self.prompt_builder.fundamental_research_json(research_snapshot),
        }
        try:
            response = self.provider.complete_fundamental_analyst(
                prompt, context, research_snapshot
            )
        except Exception as exc:
            return self._provider_exception_stage(
                step_name=AgentStepName.FUNDAMENTAL_ANALYST,
                input_json=stage_input,
                prompt=prompt,
                context=context,
                exc=exc,
                fallback=self._fallback_fundamental_analysis,
                serializer=self.prompt_builder.fundamental_analysis_json,
            )
        return self._parse_with_repair(
            step_name=AgentStepName.FUNDAMENTAL_ANALYST,
            input_json=stage_input,
            prompt=prompt,
            response=response,
            context=context,
            parser=self.output_parser.parse_fundamental_analysis,
            repair=lambda repair_prompt, raw, error: self.provider.repair_fundamental_analyst(
                repair_prompt,
                context,
                raw,
                error,
            ),
            fallback=self._fallback_fundamental_analysis,
            serializer=self.prompt_builder.fundamental_analysis_json,
            stage_label="FundamentalAnalystAgent",
        )

    def _run_sentiment_analyst(
        self,
        context: AgentContext,
        input_json: dict,
        fetched_data: FetchedDataOutput,
        research_snapshot,
        technical_analysis: TechnicalAnalysisOutput,
    ) -> PipelineStageResult:
        prompt = self.prompt_builder.build_sentiment_analyst_prompt(
            input_json,
            fetched_data,
            research_snapshot,
            technical_analysis,
        )
        stage_input = {
            **_base_stage_input(context, AgentStepName.SENTIMENT_ANALYST),
            "context": input_json,
            "fetchedData": self.prompt_builder.fetched_data_json(fetched_data),
            "research": self.prompt_builder.sentiment_research_json(research_snapshot),
            "technicalAnalysis": self.prompt_builder.technical_analysis_json(
                technical_analysis
            ),
        }
        try:
            response = self.provider.complete_sentiment_analyst(
                prompt,
                context,
                research_snapshot,
                technical_analysis,
            )
        except Exception as exc:
            return self._provider_exception_stage(
                step_name=AgentStepName.SENTIMENT_ANALYST,
                input_json=stage_input,
                prompt=prompt,
                context=context,
                exc=exc,
                fallback=self._fallback_sentiment_analysis,
                serializer=self.prompt_builder.sentiment_analysis_json,
            )
        return self._parse_with_repair(
            step_name=AgentStepName.SENTIMENT_ANALYST,
            input_json=stage_input,
            prompt=prompt,
            response=response,
            context=context,
            parser=self.output_parser.parse_sentiment_analysis,
            repair=lambda repair_prompt, raw, error: self.provider.repair_sentiment_analyst(
                repair_prompt,
                context,
                raw,
                error,
            ),
            fallback=self._fallback_sentiment_analysis,
            serializer=self.prompt_builder.sentiment_analysis_json,
            stage_label="SentimentAnalystAgent",
        )

    def _run_risk_assessment(
        self,
        context: AgentContext,
        input_json: dict,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: FundamentalAnalysisOutput,
        sentiment_analysis: SentimentAnalysisOutput,
    ) -> PipelineStageResult:
        prompt = self.prompt_builder.build_risk_assessment_prompt(
            input_json,
            technical_analysis,
            fundamental_analysis,
            sentiment_analysis,
        )
        stage_input = {
            **_base_stage_input(context, AgentStepName.RISK_MANAGER),
            "context": input_json,
            "technicalAnalysis": self.prompt_builder.technical_analysis_json(
                technical_analysis
            ),
            "fundamentalAnalysis": self.prompt_builder.fundamental_analysis_json(
                fundamental_analysis
            ),
            "sentimentAnalysis": self.prompt_builder.sentiment_analysis_json(
                sentiment_analysis
            ),
        }
        try:
            response = self.provider.complete_risk_assessment(
                prompt,
                context,
                technical_analysis,
                fundamental_analysis,
                sentiment_analysis,
            )
        except Exception as exc:
            return self._provider_exception_stage(
                step_name=AgentStepName.RISK_MANAGER,
                input_json=stage_input,
                prompt=prompt,
                context=context,
                exc=exc,
                fallback=self._fallback_risk_assessment,
                serializer=self.prompt_builder.risk_assessment_json,
            )
        return self._parse_with_repair(
            step_name=AgentStepName.RISK_MANAGER,
            input_json=stage_input,
            prompt=prompt,
            response=response,
            context=context,
            parser=self.output_parser.parse_risk_assessment,
            repair=lambda repair_prompt, raw, error: self.provider.repair_risk_assessment(
                repair_prompt,
                context,
                raw,
                error,
            ),
            fallback=self._fallback_risk_assessment,
            serializer=self.prompt_builder.risk_assessment_json,
            stage_label="RiskManagerAgent",
        )

    def _run_portfolio_manager(
        self,
        context: AgentContext,
        input_json: dict,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: FundamentalAnalysisOutput,
        sentiment_analysis: SentimentAnalysisOutput,
        risk_assessment: RiskAssessmentOutput,
    ) -> PipelineStageResult:
        prompt = self.prompt_builder.build_portfolio_manager_prompt(
            input_json,
            technical_analysis,
            fundamental_analysis,
            sentiment_analysis,
            risk_assessment,
        )
        stage_input = {
            **_base_stage_input(context, AgentStepName.PORTFOLIO_MANAGER),
            "context": input_json,
            "technicalAnalysis": self.prompt_builder.technical_analysis_json(
                technical_analysis
            ),
            "fundamentalAnalysis": self.prompt_builder.fundamental_analysis_json(
                fundamental_analysis
            ),
            "sentimentAnalysis": self.prompt_builder.sentiment_analysis_json(
                sentiment_analysis
            ),
            "riskAssessment": self.prompt_builder.risk_assessment_json(
                risk_assessment
            ),
        }
        try:
            response = self.provider.complete_portfolio_manager(
                prompt,
                context,
                technical_analysis,
                fundamental_analysis,
                sentiment_analysis,
                risk_assessment,
            )
        except Exception as exc:
            return self._provider_exception_stage(
                step_name=AgentStepName.PORTFOLIO_MANAGER,
                input_json=stage_input,
                prompt=prompt,
                context=context,
                exc=exc,
                fallback=self._fallback_portfolio_decision,
                serializer=self.prompt_builder.trading_decision_json,
            )
        return self._parse_with_repair(
            step_name=AgentStepName.PORTFOLIO_MANAGER,
            input_json=stage_input,
            prompt=prompt,
            response=response,
            context=context,
            parser=self.output_parser.parse_portfolio_decision,
            repair=lambda repair_prompt, raw, error: self.provider.repair_portfolio_manager(
                repair_prompt,
                context,
                raw,
                error,
            ),
            fallback=self._fallback_portfolio_decision,
            serializer=self.prompt_builder.trading_decision_json,
            stage_label="PortfolioManagerAgent",
        )

    def _load_price_history(self, context: AgentContext) -> list[DailyBar]:
        if self.market_data_provider is None:
            return [context.bar]

        start_date = context.bar.date - timedelta(days=40)
        try:
            bars = self.market_data_provider.load_range(
                start_date,
                context.bar.date,
                symbol=context.symbol,
                frequency=TradingFrequency.DAILY,
            )
        except Exception:
            return [context.bar]
        if not bars:
            return [context.bar]
        ordered = sorted(bars, key=lambda bar: (bar.date, bar.timestamp or context.bar.timestamp))
        return ordered

    def _technical_analysis(
        self,
        context: AgentContext,
        price_history: list[DailyBar],
        fetched_data: FetchedDataOutput,
    ) -> TechnicalAnalysisOutput:
        closes = [bar.adjusted_close for bar in price_history]
        current_price = context.bar.adjusted_close
        rsi = self._rsi(closes)
        sma_20 = self._sma(closes, 20)

        signal = MarketBias.NEUTRAL
        confidence = Decimal("0.5000")
        trend = "FLAT"

        if sma_20 is not None:
            if current_price > sma_20:
                trend = "UPWARD"
            elif current_price < sma_20:
                trend = "DOWNWARD"

        if rsi is not None and rsi < Decimal("30"):
            signal = MarketBias.BULLISH
            confidence = Decimal("0.7500")
        elif rsi is not None and rsi > Decimal("70"):
            signal = MarketBias.BEARISH
            confidence = Decimal("0.7500")
        elif sma_20 is not None and current_price > sma_20:
            signal = MarketBias.BULLISH
            confidence = Decimal("0.6500")
        elif sma_20 is not None and current_price < sma_20:
            signal = MarketBias.BEARISH
            confidence = Decimal("0.6500")

        rationale_parts = []
        if rsi is not None:
            rationale_parts.append(f"RSI(14) is {rsi}.")
        else:
            rationale_parts.append("RSI(14) is unavailable due to limited price history.")
        if sma_20 is not None:
            rationale_parts.append(f"SMA20 is {sma_20}.")
            rationale_parts.append(f"Trend is {trend}.")
        else:
            rationale_parts.append(
                "SMA20 is unavailable due to limited price history; trend remains neutral."
            )
        if fetched_data.volatility_pct is not None:
            rationale_parts.append(
                f"Observed 1-month volatility is {fetched_data.volatility_pct}%."
            )
        rationale_parts.append(f"Technical signal is {signal.value}.")

        return TechnicalAnalysisOutput(
            signal=signal,
            confidence=confidence,
            rationale=" ".join(rationale_parts),
            rsi=rsi,
            sma_20=sma_20,
            trend=trend,
            volatility_pct=fetched_data.volatility_pct,
        )

    def _volatility_pct(self, price_history: list[DailyBar]) -> Decimal | None:
        closes = [bar.adjusted_close for bar in price_history]
        if len(closes) < 2:
            return None
        returns: list[Decimal] = []
        for previous, current in zip(closes, closes[1:]):
            if previous == 0:
                continue
            returns.append((current - previous) / previous)
        if len(returns) < 2:
            return None
        mean = sum(returns, Decimal("0")) / Decimal(len(returns))
        variance = sum(
            (value - mean) * (value - mean) for value in returns
        ) / Decimal(len(returns))
        return (variance.sqrt() * Decimal("100")).quantize(Decimal("0.0001"))

    def _sma(self, closes: list[Decimal], window: int) -> Decimal | None:
        if len(closes) < window:
            return None
        selection = closes[-window:]
        return (sum(selection, Decimal("0")) / Decimal(window)).quantize(
            Decimal("0.0001")
        )

    def _rsi(self, closes: list[Decimal], window: int = 14) -> Decimal | None:
        if len(closes) <= window:
            return None
        changes = [current - previous for previous, current in zip(closes, closes[1:])]
        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]
        if not gains and not losses:
            return Decimal("50.0000")
        avg_gain = (
            sum(gains[-window:], Decimal("0")) / Decimal(window)
            if gains
            else Decimal("0")
        )
        avg_loss = (
            sum(losses[-window:], Decimal("0")) / Decimal(window)
            if losses
            else Decimal("0")
        )
        if avg_loss == 0:
            return Decimal("100.0000")
        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))
        return rsi.quantize(Decimal("0.0001"))

    def _parse_with_repair(
        self,
        *,
        step_name: AgentStepName,
        input_json: dict,
        prompt: str,
        response: AgentProviderResponse,
        context: AgentContext,
        parser: Callable[[str], object],
        repair: Callable[[str, str, str], AgentProviderResponse | None],
        fallback: Callable[[str], object],
        serializer: Callable[[object], dict],
        stage_label: str,
    ) -> PipelineStageResult:
        repair_prompt: str | None = None
        repair_raw: str | None = None
        parse_error: str | None = None
        parsing_failed = False
        fallback_reason: str | None = None
        parsed: object | None = None
        try:
            parsed = parser(response.raw_output_text)
        except AgentOutputParseError as exc:
            parse_error = str(exc)
            repair_input = response.raw_output_text
            for _ in range(2):
                repair_prompt = self.prompt_builder.build_stage_repair_prompt(
                    stage_label, repair_input, parse_error
                )
                try:
                    repair_response = repair(repair_prompt, repair_input, parse_error)
                except Exception as repair_exc:
                    parse_error = str(repair_exc)
                    parsing_failed = True
                    fallback_reason = "PROVIDER_REPAIR_EXCEPTION"
                    break

                if repair_response is None:
                    parsing_failed = True
                    fallback_reason = "REPAIR_UNAVAILABLE"
                    break

                repair_raw = repair_response.raw_output_text
                try:
                    parsed = parser(repair_raw)
                    parsing_failed = False
                    fallback_reason = None
                    break
                except AgentOutputParseError as repair_exc:
                    parse_error = str(repair_exc)
                    repair_input = repair_raw
                    parsing_failed = True
                    fallback_reason = "REPAIR_PARSE_FAILED"

            if parsed is None:
                parsed = fallback(parse_error or "Pipeline output could not be repaired.")

        parsed_json = serializer(parsed)
        parsed_json["stage"] = step_name.value
        parsed_json["fallbackUsed"] = parsing_failed
        parsed_json["fallbackReason"] = fallback_reason
        parsed_json["parseError"] = parse_error
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
            fallback_reason=fallback_reason,
            repair_prompt_text=repair_prompt,
            repair_raw_output_text=repair_raw,
        )

    def _provider_exception_stage(
        self,
        *,
        step_name: AgentStepName,
        input_json: dict,
        prompt: str,
        context: AgentContext,
        exc: Exception,
        fallback: Callable[[str], object],
        serializer: Callable[[object], dict],
    ) -> PipelineStageResult:
        parse_error = str(exc)
        parsed = fallback(parse_error)
        response = self._failed_provider_response(context)
        parsed_json = serializer(parsed)
        parsed_json["stage"] = step_name.value
        parsed_json["fallbackUsed"] = True
        parsed_json["fallbackReason"] = "PROVIDER_COMPLETE_EXCEPTION"
        parsed_json["parseError"] = parse_error
        parsed_json["modelName"] = response.model_name
        parsed_json["modelVersion"] = response.model_version
        return PipelineStageResult(
            step_name=step_name,
            input_json=input_json,
            prompt_text=prompt,
            parsed_output=parsed,
            raw_output_text=response.raw_output_text,
            parsed_output_json=parsed_json,
            parsing_failed=True,
            parse_error=parse_error,
            fallback_reason="PROVIDER_COMPLETE_EXCEPTION",
            repair_prompt_text=None,
            repair_raw_output_text=None,
        )

    def _failed_provider_response(self, context: AgentContext) -> AgentProviderResponse:
        return AgentProviderResponse(
            raw_output_text="",
            model_name=context.model_name or "deterministic-fake-multi-agent",
            model_version=None,
        )

    def _select_final_decision(
        self,
        *,
        context: AgentContext,
        proposed_decision: ParsedAgentOutput,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: FundamentalAnalysisOutput,
        sentiment_analysis: SentimentAnalysisOutput,
        risk_assessment: RiskAssessmentOutput,
        stage_results: Sequence[PipelineStageResult],
    ) -> tuple[ParsedAgentOutput, dict]:
        fallback_reason: str | None = None
        gate_input = proposed_decision

        if stage_results[-1].parsing_failed:
            gate_input = self._fallback_portfolio_decision(
                "Portfolio manager stage failed parse or repair."
            )
            fallback_reason = "PORTFOLIO_MANAGER_STAGE_FAILED"

        gate_result = self.decision_gate.apply(
            gate_input,
            context,
            risk_level=risk_assessment.risk_level.value,
        )
        final_decision = gate_result.decision
        if gate_result.audit_json["fallbackUsed"]:
            fallback_reason = gate_result.audit_json["fallbackReason"]

        degraded_stages = [
            stage.step_name.value for stage in stage_results if stage.parsing_failed
        ]
        final_json = {
            "pipeline": self.agent_name,
            "graphVersion": self.prompt_builder.prompt_version,
            "action": final_decision.action.value,
            "tradeIntent": final_decision.trade_intent.value,
            "targetExposurePct": float(final_decision.target_exposure_pct),
            "confidence": float(final_decision.confidence),
            "primaryDriver": final_decision.primary_driver.value,
            "newInformation": final_decision.new_information,
            "rationale": final_decision.rationale,
            "eventId": final_decision.event_id,
            **gate_result.audit_json,
            "fallbackUsed": fallback_reason is not None or bool(degraded_stages),
            "fallbackReason": fallback_reason,
            "degradedStages": degraded_stages,
            "pipelineStages": [stage.step_name.value for stage in stage_results],
            "pipelineStageSummary": [
                self._stage_summary(stage_result) for stage_result in stage_results
            ],
            "technicalSignal": technical_analysis.signal.value,
            "fundamentalSignal": fundamental_analysis.signal.value,
            "sentimentSignal": sentiment_analysis.signal.value,
            "riskLevel": risk_assessment.risk_level.value,
        }
        return final_decision, final_json

    def _to_log_payload(self, stage_result: PipelineStageResult) -> AgentDecisionLogPayload:
        status = ParsingStatus.FAILED if stage_result.parsing_failed else ParsingStatus.SUCCESS
        if stage_result.repair_prompt_text is not None and not stage_result.parsing_failed:
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

    def _stage_summary(self, stage_result: PipelineStageResult) -> dict:
        parsing_status = "FAILED" if stage_result.parsing_failed else "SUCCESS"
        if stage_result.repair_prompt_text is not None and not stage_result.parsing_failed:
            parsing_status = "REPAIRED"
        return {
            "pipelineStage": stage_result.step_name.value,
            "parsingStatus": parsing_status,
            "fallbackUsed": stage_result.parsing_failed,
            "fallbackReason": stage_result.fallback_reason,
        }

    def _fallback_fundamental_analysis(self, reason: str) -> FundamentalAnalysisOutput:
        return FundamentalAnalysisOutput(
            signal=MarketBias.NEUTRAL,
            confidence=Decimal("0.0000"),
            summary=f"Fundamental analysis fallback used. {reason}",
        )

    def _fallback_sentiment_analysis(self, reason: str) -> SentimentAnalysisOutput:
        return SentimentAnalysisOutput(
            signal=MarketBias.NEUTRAL,
            confidence=Decimal("0.0000"),
            summary=f"Sentiment analysis fallback used. {reason}",
        )

    def _fallback_risk_assessment(self, reason: str) -> RiskAssessmentOutput:
        return RiskAssessmentOutput(
            risk_level=RiskLevel.HIGH,
            confidence=Decimal("0.0000"),
            summary=f"Risk assessment fallback used. {reason}",
        )

    def _fallback_portfolio_decision(self, reason: str) -> ParsedAgentOutput:
        return ParsedAgentOutput(
            action=TradeAction.HOLD,
            trade_intent=TradeIntent.STAY_OUT,
            target_exposure_pct=Decimal("0.0000"),
            confidence=Decimal("0.0000"),
            primary_driver=PrimaryDriver.PORTFOLIO,
            new_information=False,
            rationale=f"Multi-agent fallback HOLD used. {reason}",
        )
