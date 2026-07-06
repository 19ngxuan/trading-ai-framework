from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas.error_schemas import ErrorResponse
from app.api.routes.comparison import router as comparison_router
from app.api.routes.broker_sync import router as broker_sync_router
from app.api.routes.events import router as events_router
from app.api.routes.experiments import router as experiments_router
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.news_events import router as news_events_router
from app.api.routes.orders import router as orders_router
from app.api.routes.options import router as options_router
from app.api.routes.paper_status import router as paper_status_router
from app.api.routes.trades import router as trades_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.scheduler.scheduler import create_scheduler


def _error_response(error_code: str, message: str, details: dict) -> dict:
    return ErrorResponse(
        errorCode=error_code,
        message=message,
        details=details,
    ).model_dump(by_alias=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    scheduler = None
    if (
        settings.scheduler_enabled
        or settings.paper_trading_scheduler_enabled
        or settings.event_scanner_enabled
    ):
        scheduler = create_scheduler(settings)
        scheduler.start()
        app.state.scheduler = scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

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
    app.include_router(comparison_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(trades_router, prefix="/api/v1")
    app.include_router(broker_sync_router, prefix="/api/v1")
    app.include_router(paper_status_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(news_events_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1")
    app.include_router(options_router, prefix="/api/v1")
    return app


app = create_app()
