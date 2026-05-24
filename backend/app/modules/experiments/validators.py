from decimal import Decimal
from typing import Any

from app.api.schemas.experiment_schemas import CreateExperimentRequest
from app.core.errors import ValidationAppError
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
