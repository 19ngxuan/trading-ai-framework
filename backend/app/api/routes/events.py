from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.event_schemas import (
    PaginatedSystemEventResponse,
    SystemEventResponse,
)
from app.core.errors import NotFoundAppError
from app.domain.enums import EventLevel, SystemEventType
from app.persistence.database import get_session
from app.persistence.repositories import ExperimentRepository, SystemEventLogRepository

router = APIRouter(tags=["events"])


def _ensure_experiment_exists(session: Session, experiment_id: int) -> None:
    if ExperimentRepository(session).get_by_id(experiment_id) is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )


def _list_events(
    session: Session,
    *,
    experiment_id: int | None,
    level: EventLevel | None,
    event_type: SystemEventType | None,
    limit: int,
    offset: int,
) -> PaginatedSystemEventResponse:
    repository = SystemEventLogRepository(session)
    items = repository.list_filtered(
        experiment_id=experiment_id,
        level=level,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    total = repository.count_filtered(
        experiment_id=experiment_id,
        level=level,
        event_type=event_type,
    )
    return PaginatedSystemEventResponse(
        items=[SystemEventResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/events", response_model=PaginatedSystemEventResponse)
def list_events(
    experiment_id: int | None = Query(default=None, alias="experimentId"),
    level: EventLevel | None = None,
    event_type: SystemEventType | None = Query(default=None, alias="eventType"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedSystemEventResponse:
    if experiment_id is not None:
        _ensure_experiment_exists(session, experiment_id)
    return _list_events(
        session,
        experiment_id=experiment_id,
        level=level,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/experiments/{experiment_id}/events",
    response_model=PaginatedSystemEventResponse,
)
def list_experiment_events(
    experiment_id: int,
    level: EventLevel | None = None,
    event_type: SystemEventType | None = Query(default=None, alias="eventType"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedSystemEventResponse:
    _ensure_experiment_exists(session, experiment_id)
    return _list_events(
        session,
        experiment_id=experiment_id,
        level=level,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
