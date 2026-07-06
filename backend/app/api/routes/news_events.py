from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.news_event_schemas import (
    EventDecisionResponse,
    NewsEventDetailResponse,
    NewsEventResponse,
    PaginatedEventDecisionResponse,
    PaginatedNewsEventResponse,
)
from app.core.errors import NotFoundAppError
from app.domain.enums import EventDecisionStatus, NewsEventSeverity, NewsEventType
from app.persistence.database import get_session
from app.persistence.models import EventDecisionModel, NewsEventModel
from app.persistence.repositories import (
    EventAssetImpactRepository,
    EventDecisionRepository,
    ExperimentRepository,
    NewsEventRepository,
)

router = APIRouter(tags=["news-events"])


def _ensure_experiment_exists(session: Session, experiment_id: int) -> None:
    if ExperimentRepository(session).get_by_id(experiment_id) is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )


@router.get("/news-events", response_model=PaginatedNewsEventResponse)
def list_news_events(
    symbol: str | None = None,
    event_type: NewsEventType | None = Query(default=None, alias="eventType"),
    severity: NewsEventSeverity | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedNewsEventResponse:
    repository = NewsEventRepository(session)
    items = repository.list_filtered(
        symbol=symbol,
        event_type=event_type,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    total_statement = select(func.count(NewsEventModel.id))
    if symbol is not None:
        total_statement = total_statement.where(
            NewsEventModel.affected_symbols_json.op("?")(symbol.upper())
        )
    if event_type is not None:
        total_statement = total_statement.where(NewsEventModel.event_type == event_type)
    if severity is not None:
        total_statement = total_statement.where(NewsEventModel.severity == severity)
    return PaginatedNewsEventResponse(
        items=[NewsEventResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=int(session.scalar(total_statement) or 0),
    )


@router.get("/news-events/{event_id}", response_model=NewsEventDetailResponse)
def get_news_event(
    event_id: int,
    session: Session = Depends(get_session),
) -> NewsEventDetailResponse:
    event = NewsEventRepository(session).get(event_id)
    if event is None:
        raise NotFoundAppError(
            "News event was not found.",
            details={"eventId": event_id},
        )
    payload = NewsEventResponse.model_validate(event).model_dump(by_alias=False)
    payload["impacts"] = [
        item
        for item in EventAssetImpactRepository(session).list_by_event(event_id)
    ]
    return NewsEventDetailResponse.model_validate(payload)


@router.get(
    "/experiments/{experiment_id}/news-events",
    response_model=PaginatedNewsEventResponse,
)
def list_experiment_news_events(
    experiment_id: int,
    event_type: NewsEventType | None = Query(default=None, alias="eventType"),
    severity: NewsEventSeverity | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedNewsEventResponse:
    _ensure_experiment_exists(session, experiment_id)
    base_statement = (
        select(NewsEventModel)
        .join(EventDecisionModel, EventDecisionModel.event_id == NewsEventModel.id)
        .where(EventDecisionModel.experiment_id == experiment_id)
    )
    if event_type is not None:
        base_statement = base_statement.where(NewsEventModel.event_type == event_type)
    if severity is not None:
        base_statement = base_statement.where(NewsEventModel.severity == severity)
    statement = (
        base_statement.order_by(NewsEventModel.timestamp.desc(), NewsEventModel.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(statement))
    total = int(
        session.scalar(
            select(func.count()).select_from(base_statement.subquery())
        )
        or 0
    )
    return PaginatedNewsEventResponse(
        items=[NewsEventResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/experiments/{experiment_id}/event-decisions",
    response_model=PaginatedEventDecisionResponse,
)
def list_experiment_event_decisions(
    experiment_id: int,
    status: EventDecisionStatus | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedEventDecisionResponse:
    _ensure_experiment_exists(session, experiment_id)
    items = EventDecisionRepository(session).list_by_experiment(
        experiment_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    total_statement = select(func.count(EventDecisionModel.id)).where(
        EventDecisionModel.experiment_id == experiment_id
    )
    if status is not None:
        total_statement = total_statement.where(EventDecisionModel.status == status)
    return PaginatedEventDecisionResponse(
        items=[EventDecisionResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=int(session.scalar(total_statement) or 0),
    )
