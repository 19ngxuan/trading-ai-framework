from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas.error_schemas import ErrorResponse
from app.api.routes.experiments import router as experiments_router
from app.api.routes.health import router as health_router
from app.api.routes.options import router as options_router
from app.core.config import get_settings
from app.core.errors import AppError


def _error_response(error_code: str, message: str, details: dict) -> dict:
    return ErrorResponse(
        errorCode=error_code,
        message=message,
        details=details,
    ).model_dump(by_alias=True)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    def handle_app_error(_, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_response(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    def handle_request_validation_error(_, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_response(
                "VALIDATION_ERROR",
                "Request validation failed.",
                {"errors": exc.errors()},
            ),
        )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(experiments_router, prefix="/api/v1")
    app.include_router(options_router, prefix="/api/v1")
    return app


app = create_app()
