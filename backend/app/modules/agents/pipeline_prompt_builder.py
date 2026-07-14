import json
from typing import Any

from app.modules.agents.pipeline_types import (
    FetchedDataOutput,
    FundamentalAnalysisOutput,
    RiskAssessmentOutput,
    SentimentAnalysisOutput,
    TechnicalAnalysisOutput,
)
from app.modules.agents.prompt_builder import PromptBuilder
from app.modules.agents.research_providers import (
    FundamentalResearchSnapshot,
    SentimentResearchSnapshot,
)
from app.modules.agents.types import ParsedAgentOutput


PIPELINE_PROMPT_VERSION = "multi-agent-graph-v2-target-exposure"


class PipelinePromptBuilder(PromptBuilder):
    prompt_version = PIPELINE_PROMPT_VERSION

    def build_fundamental_analyst_prompt(
        self,
        input_json: dict[str, Any],
        fetched_data: FetchedDataOutput,
        research_snapshot: FundamentalResearchSnapshot,
    ) -> str:
        enriched = {
            **input_json,
            "fetchedData": self.fetched_data_json(fetched_data),
            "fundamentalResearch": self.fundamental_research_json(research_snapshot),
        }
        return self._guarded_prompt(
            "FundamentalAnalystAgent",
            (
                "Return strict JSON with signal BULLISH, BEARISH, or NEUTRAL, "
                "confidence, and summary. If the framework did not provide structured "
                "fundamental inputs, explicitly say so and stay conservative."
            ),
            enriched,
        )

    def build_sentiment_analyst_prompt(
        self,
        input_json: dict[str, Any],
        fetched_data: FetchedDataOutput,
        research_snapshot: SentimentResearchSnapshot,
        technical_analysis: TechnicalAnalysisOutput,
    ) -> str:
        enriched = {
            **input_json,
            "fetchedData": self.fetched_data_json(fetched_data),
            "sentimentResearch": self.sentiment_research_json(research_snapshot),
            "technicalAnalysis": self.technical_analysis_json(technical_analysis),
        }
        return self._guarded_prompt(
            "SentimentAnalystAgent",
            (
                "Return strict JSON with signal BULLISH, BEARISH, or NEUTRAL, "
                "confidence, and summary. If the framework did not provide "
                "structured sentiment inputs, explicitly say so and stay conservative."
            ),
            enriched,
        )

    def build_technical_analyst_prompt(
        self,
        input_json: dict[str, Any],
        fetched_data: FetchedDataOutput,
        technical_snapshot: TechnicalAnalysisOutput,
    ) -> str:
        enriched = {
            **input_json,
            "fetchedData": self.fetched_data_json(fetched_data),
            "technicalIndicators": self.technical_analysis_json(technical_snapshot),
        }
        return self._guarded_prompt(
            "TechnicalAnalystAgent",
            (
                "Return strict JSON with signal BULLISH, BEARISH, or NEUTRAL, "
                "confidence, summary, indicators, timeHorizonSignals, and riskNotes. "
                "Base the assessment only on the framework-provided deterministic "
                "technical indicators."
            ),
            enriched,
        )

    def build_risk_assessment_prompt(
        self,
        input_json: dict[str, Any],
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: FundamentalAnalysisOutput,
        sentiment_analysis: SentimentAnalysisOutput,
    ) -> str:
        enriched = {
            **input_json,
            "technicalAnalysis": self.technical_analysis_json(technical_analysis),
            "fundamentalAnalysis": self.fundamental_analysis_json(
                fundamental_analysis
            ),
            "sentimentAnalysis": self.sentiment_analysis_json(sentiment_analysis),
        }
        return self._guarded_prompt(
            "RiskManagerAgent",
            (
                "Return strict JSON with riskLevel LOW, MEDIUM, or HIGH, confidence, "
                "and summary."
            ),
            enriched,
        )

    def build_portfolio_manager_prompt(
        self,
        input_json: dict[str, Any],
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: FundamentalAnalysisOutput,
        sentiment_analysis: SentimentAnalysisOutput,
        risk_assessment: RiskAssessmentOutput,
    ) -> str:
        enriched = {
            **input_json,
            "technicalAnalysis": self.technical_analysis_json(technical_analysis),
            "fundamentalAnalysis": self.fundamental_analysis_json(
                fundamental_analysis
            ),
            "sentimentAnalysis": self.sentiment_analysis_json(sentiment_analysis),
            "riskAssessment": self.risk_assessment_json(risk_assessment),
        }
        return self._guarded_prompt(
            "PortfolioManagerAgent",
            (
                "Return strict JSON with action BUY, SELL, or HOLD; tradeIntent "
                "OPEN_LONG, ADD_TO_LONG, HOLD_POSITION, REDUCE_LONG, CLOSE_LONG, "
                "or STAY_OUT; targetExposurePct between 0 and 1; confidence; "
                "primaryDriver TECHNICAL, FUNDAMENTAL, SENTIMENT, RISK, PORTFOLIO, "
                "or EVENT_RISK; newInformation boolean; rationale; optional eventId. "
                "BUY increases exposure, SELL reduces exposure. You are advisory "
                "only; RiskCheck will make the final execution determination."
            ),
            enriched,
        )

    def build_stage_repair_prompt(
        self, stage_name: str, raw_output_text: str, error_message: str
    ) -> str:
        example = self._stage_repair_example(stage_name)
        return (
            f"Repair {stage_name} output into strict valid JSON for that stage. "
            "Return only raw JSON. No markdown. No explanation. "
            f"Use this shape: {json.dumps(example, sort_keys=True)}. "
            f"Parse error: {error_message}. Previous output: {raw_output_text}"
        )

    def fetched_data_json(self, output: FetchedDataOutput) -> dict[str, Any]:
        return {
            "currentPrice": float(output.current_price),
            "historyLength": output.history_length,
            "volatilityPct": float(output.volatility_pct)
            if output.volatility_pct is not None
            else None,
            "fundamentalDataAvailable": output.fundamental_data_available,
            "sentimentDataAvailable": output.sentiment_data_available,
            "marketDataAvailable": output.market_data_available,
            "intradayDataAvailable": output.intraday_data_available,
            "benchmarkDataAvailable": output.benchmark_data_available,
            "newsDataAvailable": output.news_data_available,
            "transcriptDataAvailable": output.transcript_data_available,
            "intradayHistoryLength": output.intraday_history_length,
            "benchmarkHistoryLength": output.benchmark_history_length,
            "rationale": output.rationale,
        }

    def technical_analysis_json(
        self, output: TechnicalAnalysisOutput
    ) -> dict[str, Any]:
        return {
            "signal": output.signal.value,
            "confidence": float(output.confidence),
            "rationale": output.rationale,
            "rsi": float(output.rsi) if output.rsi is not None else None,
            "sma20": float(output.sma_20) if output.sma_20 is not None else None,
            "trend": output.trend,
            "volatilityPct": float(output.volatility_pct)
            if output.volatility_pct is not None
            else None,
            "indicators": output.indicators,
            "timeHorizonSignals": output.time_horizon_signals,
            "riskNotes": output.risk_notes,
        }

    def fundamental_analysis_json(
        self, output: FundamentalAnalysisOutput
    ) -> dict[str, Any]:
        return {
            "signal": output.signal.value,
            "confidence": float(output.confidence),
            "summary": output.summary,
        }

    def sentiment_analysis_json(
        self, output: SentimentAnalysisOutput
    ) -> dict[str, Any]:
        return {
            "signal": output.signal.value,
            "confidence": float(output.confidence),
            "summary": output.summary,
        }

    def risk_assessment_json(self, output: RiskAssessmentOutput) -> dict[str, Any]:
        return {
            "riskLevel": output.risk_level.value,
            "confidence": float(output.confidence),
            "summary": output.summary,
        }

    def trading_decision_json(self, output: ParsedAgentOutput) -> dict[str, Any]:
        return {
            "action": output.action.value,
            "tradeIntent": output.trade_intent.value,
            "targetExposurePct": float(output.target_exposure_pct),
            "confidence": float(output.confidence),
            "primaryDriver": output.primary_driver.value,
            "newInformation": output.new_information,
            "rationale": output.rationale,
            "eventId": output.event_id,
        }

    def fundamental_research_json(
        self, snapshot: FundamentalResearchSnapshot
    ) -> dict[str, Any]:
        return {
            "peRatio": float(snapshot.pe_ratio) if snapshot.pe_ratio is not None else None,
            "forwardPe": float(snapshot.forward_pe)
            if snapshot.forward_pe is not None
            else None,
            "marketCap": float(snapshot.market_cap)
            if snapshot.market_cap is not None
            else None,
            "dividendYield": float(snapshot.dividend_yield)
            if snapshot.dividend_yield is not None
            else None,
            "profitMargins": float(snapshot.profit_margins)
            if snapshot.profit_margins is not None
            else None,
            "revenueGrowth": float(snapshot.revenue_growth)
            if snapshot.revenue_growth is not None
            else None,
            "notes": snapshot.notes,
            "rawData": snapshot.raw_data,
            "analystEstimates": snapshot.analyst_estimates,
            "analystRatings": snapshot.analyst_ratings,
            "source": snapshot.source,
            "dataAvailable": snapshot.data_available,
        }

    def sentiment_research_json(
        self, snapshot: SentimentResearchSnapshot
    ) -> dict[str, Any]:
        return {
            "summary": snapshot.summary,
            "headlines": list(snapshot.headlines),
            "signal": snapshot.signal,
            "confidence": float(snapshot.confidence)
            if snapshot.confidence is not None
            else None,
            "rawData": snapshot.raw_data,
            "newsItems": list(snapshot.news_items),
            "analystComments": list(snapshot.analyst_comments),
            "transcriptSummaries": list(snapshot.transcript_summaries),
            "sourceWeights": snapshot.source_weights,
            "timeWeighting": snapshot.time_weighting,
            "duplicateCount": snapshot.duplicate_count,
            "contradictionNotes": list(snapshot.contradiction_notes),
            "source": snapshot.source,
            "newsAvailable": snapshot.news_available,
            "transcriptAvailable": snapshot.transcript_available,
        }

    def _guarded_prompt(
        self, stage_name: str, instruction: str, input_json: dict[str, Any]
    ) -> str:
        return (
            f"{stage_name} is a deterministic advisory stage for a controlled "
            "trading workflow. It must not call tools, broker, Alpaca, order, "
            "trade, portfolio, scheduler, repository, persistence, or market-data "
            "APIs. RiskCheck remains mandatory and authoritative after the final "
            f"decision. {instruction} Input: {input_json}"
        )

    def _stage_repair_example(self, stage_name: str) -> dict[str, Any]:
        examples: dict[str, dict[str, Any]] = {
            "TechnicalAnalystAgent": {
                "signal": "NEUTRAL",
                "confidence": 0.0,
                "summary": "Technical indicators are mixed.",
                "indicators": {},
                "timeHorizonSignals": {},
                "riskNotes": [],
            },
            "FundamentalAnalystAgent": {
                "signal": "NEUTRAL",
                "confidence": 0.0,
                "summary": "No structured fundamental inputs were provided.",
            },
            "SentimentAnalystAgent": {
                "signal": "NEUTRAL",
                "confidence": 0.0,
                "summary": "No structured sentiment inputs were provided.",
            },
            "RiskManagerAgent": {
                "riskLevel": "MEDIUM",
                "confidence": 0.0,
                "summary": "Risk is neutral based on the provided stage inputs.",
            },
            "PortfolioManagerAgent": {
                "action": "HOLD",
                "tradeIntent": "STAY_OUT",
                "targetExposurePct": 0.0,
                "confidence": 0.0,
                "primaryDriver": "PORTFOLIO",
                "newInformation": False,
                "rationale": "Insufficient valid signal to change exposure.",
                "eventId": None,
            },
        }
        return examples.get(stage_name, {})
