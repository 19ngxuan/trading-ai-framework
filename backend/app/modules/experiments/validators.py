from decimal import Decimal
from typing import Any

from app.api.schemas.experiment_schemas import CreateExperimentRequest
from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.domain.enums import ExperimentMode, StrategyType, TradingFrequency
from app.modules.execution.position_sizing import (
    PositionSizingConfigurationError,
    validate_position_sizing_config,
)


def _validate_risk_config(risk_config: dict[str, Any]) -> None:
    fallback_action = risk_config.get("fallbackAction")
    if fallback_action is not None and fallback_action != "HOLD":
        raise ValidationAppError(
            "fallbackAction must be HOLD.",
            details={"field": "strategyConfig.parametersJson.riskConfig.fallbackAction"},
        )


def validate_create_experiment_request(request: CreateExperimentRequest) -> None:
    settings = get_settings()
    if request.asset_symbol != "SPY":
        raise ValidationAppError(
            "assetSymbol must be SPY in V1.",
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

    if request.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
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
        if request.strategy_config.position_sizing_type not in {
            None,
            "FIXED_QUANTITY",
        }:
            raise ValidationAppError(
                "Paper trading smoke-test uses fixed 1-share sizing only.",
                details={
                    "field": "strategyConfig.positionSizingType",
                    "value": request.strategy_config.position_sizing_type,
                },
            )
        if (
            request.strategy_config.position_sizing_value is not None
            and request.strategy_config.position_sizing_value != Decimal("1")
        ):
            raise ValidationAppError(
                "Paper trading smoke-test positionSizingValue must be 1 when provided.",
                details={"field": "strategyConfig.positionSizingValue"},
            )
    elif request.strategy_type is StrategyType.OPENING_RANGE_BREAKOUT:
        if request.mode is not ExperimentMode.HISTORICAL_SIMULATION:
            raise ValidationAppError(
                "Opening Range Breakout supports HISTORICAL_SIMULATION mode only.",
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

    try:
        validate_position_sizing_config(
            request.strategy_config.position_sizing_type,
            request.strategy_config.position_sizing_value,
        )
    except PositionSizingConfigurationError as exc:
        raise ValidationAppError(
            str(exc),
            details={
                "field": "strategyConfig.positionSizingValue",
                "positionSizingType": request.strategy_config.position_sizing_type
                or "ALL_IN",
            },
        ) from exc

    parameters_json = request.strategy_config.parameters_json or {}
    risk_config = parameters_json.get("riskConfig")
    if isinstance(risk_config, dict):
        _validate_risk_config(risk_config)
