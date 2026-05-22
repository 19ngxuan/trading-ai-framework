from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    error_code: str
    message: str
    status_code: int
    details: dict[str, Any] = field(default_factory=dict)


class ValidationAppError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details or {},
        )


class NotFoundAppError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            error_code="EXPERIMENT_NOT_FOUND",
            message=message,
            status_code=404,
            details=details or {},
        )


class InvalidStatusAppError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            error_code="INVALID_EXPERIMENT_STATUS",
            message=message,
            status_code=409,
            details=details or {},
        )


class InvalidExperimentConfigurationAppError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            error_code="INVALID_EXPERIMENT_CONFIGURATION",
            message=message,
            status_code=409,
            details=details or {},
        )
