from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.experiment_schemas import (
    CreateExperimentRequest,
    CreateExperimentResponse,
    ExperimentActionResponse,
    ExperimentDetailResponse,
    PaginatedExperimentSummaryResponse,
)
from app.api.schemas.execution_schemas import RunNextStepRequest, RunNextStepResponse
from app.domain.enums import ExperimentMode, ExperimentStatus, StrategyType
from app.core.errors import NotFoundAppError
from app.modules.execution.paper_step_runner import PaperTradingStepRunner
from app.modules.execution.step_runner import HistoricalStepRunner
from app.modules.experiments.service import ExperimentService
from app.persistence.database import get_session
from app.persistence.repositories import ExperimentRepository

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
    experiment_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> ExperimentActionResponse:
    service = ExperimentService(session)
    return service.start_experiment(experiment_id, background_tasks)


@router.post(
    "/{experiment_id}/run-next-step",
    response_model=RunNextStepResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_next_step(
    experiment_id: int,
    payload: RunNextStepRequest | None = None,
    session: Session = Depends(get_session),
) -> RunNextStepResponse:
    _ = payload
    experiment = ExperimentRepository(session).get_by_id(experiment_id)
    if experiment is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )
    if experiment.mode is ExperimentMode.PAPER_TRADING:
        result = PaperTradingStepRunner().run_next_step(experiment_id)
    else:
        result = HistoricalStepRunner().run_next_step(experiment_id)
    return RunNextStepResponse(
        experimentId=result.experiment_id,
        executionStepId=result.execution_step_id,
        status=result.status.value,
        message=result.message,
    )


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
