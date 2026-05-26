from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.broker_sync_schemas import (
    BrokerSyncLogResponse,
    PaginatedBrokerSyncLogResponse,
)
from app.core.errors import NotFoundAppError
from app.persistence.database import get_session
from app.persistence.repositories import BrokerSyncLogRepository, ExperimentRepository

router = APIRouter(prefix="/experiments", tags=["broker-sync"])


def _ensure_experiment_exists(session: Session, experiment_id: int) -> None:
    if ExperimentRepository(session).get_by_id(experiment_id) is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )


@router.get(
    "/{experiment_id}/broker-sync-logs",
    response_model=PaginatedBrokerSyncLogResponse,
)
def list_experiment_broker_sync_logs(
    experiment_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedBrokerSyncLogResponse:
    _ensure_experiment_exists(session, experiment_id)
    repository = BrokerSyncLogRepository(session)
    items = repository.list_by_experiment_paginated(experiment_id, limit, offset)
    total = repository.count_by_experiment(experiment_id)
    return PaginatedBrokerSyncLogResponse(
        items=[BrokerSyncLogResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )
