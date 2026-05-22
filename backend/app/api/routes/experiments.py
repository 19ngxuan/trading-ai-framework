from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.experiment_schemas import (
    CreateExperimentRequest,
    CreateExperimentResponse,
    ExperimentActionResponse,
    ExperimentDetailResponse,
    PaginatedExperimentSummaryResponse,
)
from app.domain.enums import ExperimentMode, ExperimentStatus, StrategyType
from app.modules.experiments.service import ExperimentService
from app.persistence.database import get_session

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=CreateExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: CreateExperimentRequest, session: Session = Depends(get_session)
) -> CreateExperimentResponse:
    service = ExperimentService(session)
    created = service.create_experiment(payload)
    return CreateExperimentResponse(**created)


@router.get("", response_model=PaginatedExperimentSummaryResponse)
def list_experiments(
    status_filter: ExperimentStatus | None = Query(default=None, alias="status"),
    strategy_type: StrategyType | None = Query(default=None, alias="strategyType"),
    mode: ExperimentMode | None = Query(default=None, alias="mode"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedExperimentSummaryResponse:
    service = ExperimentService(session)
    return service.list_experiments(status_filter, strategy_type, mode, limit, offset)


@router.get("/{experiment_id}", response_model=ExperimentDetailResponse)
def get_experiment_detail(
    experiment_id: int, session: Session = Depends(get_session)
) -> ExperimentDetailResponse:
    service = ExperimentService(session)
    return service.get_experiment_detail(experiment_id)


@router.post(
    "/{experiment_id}/start",
    response_model=ExperimentActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_experiment(
    experiment_id: int, session: Session = Depends(get_session)
) -> ExperimentActionResponse:
    service = ExperimentService(session)
    return service.apply_lifecycle_action(experiment_id, "start")


@router.post("/{experiment_id}/pause", response_model=ExperimentActionResponse)
def pause_experiment(
    experiment_id: int, session: Session = Depends(get_session)
) -> ExperimentActionResponse:
    service = ExperimentService(session)
    return service.apply_lifecycle_action(experiment_id, "pause")


@router.post(
    "/{experiment_id}/resume",
    response_model=ExperimentActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def resume_experiment(
    experiment_id: int, session: Session = Depends(get_session)
) -> ExperimentActionResponse:
    service = ExperimentService(session)
    return service.apply_lifecycle_action(experiment_id, "resume")


@router.post("/{experiment_id}/stop", response_model=ExperimentActionResponse)
def stop_experiment(
    experiment_id: int, session: Session = Depends(get_session)
) -> ExperimentActionResponse:
    service = ExperimentService(session)
    return service.apply_lifecycle_action(experiment_id, "stop")
