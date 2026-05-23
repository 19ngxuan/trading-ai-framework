from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.metrics_schemas import (
    MetricSnapshotResponse,
    PaginatedMetricSnapshotResponse,
    PaginatedPortfolioSnapshotResponse,
    PortfolioSnapshotResponse,
)
from app.core.errors import NotFoundAppError
from app.persistence.repositories import (
    ExperimentRepository,
    MetricSnapshotRepository,
    PortfolioSnapshotRepository,
)
from app.persistence.database import get_session

router = APIRouter(prefix="/experiments", tags=["metrics"])


def _ensure_experiment_exists(session: Session, experiment_id: int) -> None:
    if ExperimentRepository(session).get_by_id(experiment_id) is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )


@router.get(
    "/{experiment_id}/metrics",
    response_model=PaginatedMetricSnapshotResponse,
)
def list_metric_snapshots(
    experiment_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedMetricSnapshotResponse:
    _ensure_experiment_exists(session, experiment_id)
    repository = MetricSnapshotRepository(session)
    items = repository.list_by_experiment_paginated(experiment_id, limit, offset)
    total = repository.count_by_experiment(experiment_id)
    return PaginatedMetricSnapshotResponse(
        items=[MetricSnapshotResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/{experiment_id}/portfolio-snapshots",
    response_model=PaginatedPortfolioSnapshotResponse,
)
def list_portfolio_snapshots(
    experiment_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedPortfolioSnapshotResponse:
    _ensure_experiment_exists(session, experiment_id)
    repository = PortfolioSnapshotRepository(session)
    items = repository.list_by_experiment_paginated(experiment_id, limit, offset)
    total = repository.count_by_experiment(experiment_id)
    return PaginatedPortfolioSnapshotResponse(
        items=[PortfolioSnapshotResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )
