from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.trade_schemas import PaginatedTradeResponse, TradeResponse
from app.core.errors import NotFoundAppError
from app.persistence.database import get_session
from app.persistence.repositories import ExperimentRepository, TradeRepository

router = APIRouter(prefix="/experiments", tags=["trades"])


def _ensure_experiment_exists(session: Session, experiment_id: int) -> None:
    if ExperimentRepository(session).get_by_id(experiment_id) is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )


@router.get("/{experiment_id}/trades", response_model=PaginatedTradeResponse)
def list_experiment_trades(
    experiment_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedTradeResponse:
    _ensure_experiment_exists(session, experiment_id)
    repository = TradeRepository(session)
    items = repository.list_by_experiment_paginated(experiment_id, limit, offset)
    total = repository.count_by_experiment(experiment_id)
    return PaginatedTradeResponse(
        items=[TradeResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )
