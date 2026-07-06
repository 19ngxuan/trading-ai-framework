from decimal import Decimal
from typing import Any

from app.api.schemas.experiment_schemas import CreateExperimentRequest
from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.domain.assets import SPY_SYMBOL
from app.domain.assets import is_supported_equity_symbol
from app.domain.assets import normalize_symbol
from app.domain.enums import AgentMode
from app.domain.enums import ExperimentMode, StrategyType, TradingFrequency


def _validate_risk_config(risk_config: dict[str, Any]) -> None:
    fallback_action = risk_config.get("fallbackAction")
    if fallback_action is not None and fallback_action != "HOLD":
        raise ValidationAppError(
            "fallbackAction must be HOLD.",
            details={"field": "strategyConfig.parametersJson.riskConfig.fallbackAction"},
        )


def validate_create_experiment_request(request: CreateExperimentRequest) -> None:
    settings = get_settings()
    asset_symbol = normalize_symbol(request.asset_symbol)
    if not is_supported_equity_symbol(asset_symbol):
        raise ValidationAppError(
            "assetSymbol is not supported.",
            details={"field": "assetSymbol", "value": request.asset_symbol},
        )
    if (
        request.mode is ExperimentMode.HISTORICAL_SIMULATION
        and asset_symbol != SPY_SYMBOL
    ):
        raise ValidationAppError(
            "Historical simulation supports SPY only in this release.",
            details={"field": "assetSymbol", "value": request.asset_symbol},
        )

    if request.initial_capital <= Decimal("0"):
        raise ValidationAppError(
            "initialCapital must be positive.",
            details={"field": "initialCapital"},
        )

    if request.start_date > request.end_date:
        raise ValidationAppError(
            "startDate must be less than or equal to endDate.",
            details={"field": "startDate"},
        )

    if request.fee_value < Decimal("0"):
        raise ValidationAppError(
            "feeValue must be greater than or equal to 0.",
            details={"field": "feeValue"},
        )

    if (
        request.mode is ExperimentMode.HISTORICAL_SIMULATION
        and request.strategy_type is StrategyType.AGENTIC_AI
    ):
        raise ValidationAppError(
            "Agentic AI is supported for PAPER_TRADING mode only.",
            details={
                "field": "strategyType",
                "mode": request.mode.value,
                "strategyType": request.strategy_type.value,
            },
        )

    if request.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
        if asset_symbol != SPY_SYMBOL:
            raise ValidationAppError(
                "Paper trading smoke-test supports SPY only.",
                details={"field": "assetSymbol", "value": request.asset_symbol},
            )
        if not settings.paper_trading_test_mode_enabled:
            raise ValidationAppError(
                "Paper trading smoke-test strategy is disabled.",
                details={
                    "field": "strategyType",
                    "requiredConfig": "PAPER_TRADING_TEST_MODE_ENABLED=true",
                },
            )
        if request.mode is not ExperimentMode.PAPER_TRADING:
            raise ValidationAppError(
                "Paper trading smoke-test supports PAPER_TRADING mode only.",
                details={"field": "mode", "value": request.mode.value},
            )
        if request.trading_frequency is not TradingFrequency.TEST_1_MIN:
            raise ValidationAppError(
                "Paper trading smoke-test supports TEST_1_MIN frequency only.",
                details={
                    "field": "tradingFrequency",
                    "value": request.trading_frequency.value,
                },
            )
    elif request.strategy_type is StrategyType.OPENING_RANGE_BREAKOUT:
        if asset_symbol != SPY_SYMBOL:
            raise ValidationAppError(
                "Opening Range Breakout supports SPY only.",
                details={"field": "assetSymbol", "value": request.asset_symbol},
            )
        if request.mode not in {
            ExperimentMode.HISTORICAL_SIMULATION,
            ExperimentMode.PAPER_TRADING,
        }:
            raise ValidationAppError(
                "Opening Range Breakout supports HISTORICAL_SIMULATION or PAPER_TRADING mode only.",
                details={"field": "mode", "value": request.mode.value},
            )
        if request.trading_frequency is not TradingFrequency.INTRADAY_5_MIN:
            raise ValidationAppError(
                "Opening Range Breakout supports INTRADAY_5_MIN frequency only.",
                details={
                    "field": "tradingFrequency",
                    "value": request.trading_frequency.value,
                },
            )
    elif request.trading_frequency is TradingFrequency.INTRADAY_5_MIN:
        raise ValidationAppError(
            "INTRADAY_5_MIN frequency is supported only for Opening Range Breakout.",
            details={
                "field": "tradingFrequency",
                "strategyType": request.strategy_type.value,
            },
        )
    elif request.trading_frequency is TradingFrequency.TEST_1_MIN:
        raise ValidationAppError(
            "TEST_1_MIN frequency is supported only for paper trading smoke-test.",
            details={
                "field": "tradingFrequency",
                "strategyType": request.strategy_type.value,
            },
        )
    elif (
        request.trading_frequency is TradingFrequency.HOURLY
        and request.strategy_type is not StrategyType.AGENTIC_AI
    ):
        raise ValidationAppError(
            "HOURLY frequency is supported only for Agentic AI paper trading.",
            details={
                "field": "tradingFrequency",
                "strategyType": request.strategy_type.value,
            },
        )

    if request.mode is ExperimentMode.PAPER_TRADING:
        supported_paper_configs = {
            (StrategyType.BUY_AND_HOLD, TradingFrequency.DAILY),
            (StrategyType.MOVING_AVERAGE, TradingFrequency.DAILY),
            (StrategyType.OPENING_RANGE_BREAKOUT, TradingFrequency.INTRADAY_5_MIN),
            (StrategyType.AGENTIC_AI, TradingFrequency.DAILY),
            (StrategyType.AGENTIC_AI, TradingFrequency.HOURLY),
        }
        if request.strategy_type is not StrategyType.PAPER_TRADING_SMOKE_TEST and (
            request.strategy_type,
            request.trading_frequency,
        ) not in supported_paper_configs:
            raise ValidationAppError(
                "Paper trading supports configured equity assets with these combinations: "
                "BUY_AND_HOLD DAILY, MOVING_AVERAGE DAILY, "
                "AGENTIC_AI DAILY/HOURLY, or "
                "OPENING_RANGE_BREAKOUT INTRADAY_5_MIN.",
                details={
                    "field": "strategyType",
                    "strategyType": request.strategy_type.value,
                    "tradingFrequency": request.trading_frequency.value,
                },
            )
        if request.strategy_type is StrategyType.AGENTIC_AI:
            agent_mode = request.strategy_config.agent_mode or AgentMode.SINGLE_AGENT
            if agent_mode not in {AgentMode.SINGLE_AGENT, AgentMode.PIPELINE}:
                raise ValidationAppError(
                    "Agentic AI paper trading supports SINGLE_AGENT or PIPELINE (Multi Agent) mode only.",
                    details={
                        "field": "strategyConfig.agentMode",
                        "value": agent_mode.value,
                    },
                )
            model_name = request.strategy_config.model_name or settings.scadsai_default_model
            if model_name not in settings.scadsai_allowed_model_list:
                raise ValidationAppError(
                    "Selected ScaDS.AI model is not allowed.",
                    details={
                        "field": "strategyConfig.modelName",
                        "value": model_name,
                        "allowedModels": settings.scadsai_allowed_model_list,
                    },
                )

    if request.strategy_config.moving_average_window is not None:
        if request.strategy_config.moving_average_window <= 0:
            raise ValidationAppError(
                "movingAverageWindow must be positive when provided.",
                details={"field": "strategyConfig.movingAverageWindow"},
            )

    if request.strategy_config.confidence_threshold is not None:
        threshold = request.strategy_config.confidence_threshold
        if threshold < Decimal("0") or threshold > Decimal("1"):
            raise ValidationAppError(
                "confidenceThreshold must be between 0 and 1 when provided.",
                details={"field": "strategyConfig.confidenceThreshold"},
            )

    parameters_json = request.strategy_config.parameters_json or {}
    risk_config = parameters_json.get("riskConfig")
    if isinstance(risk_config, dict):
        _validate_risk_config(risk_config)
