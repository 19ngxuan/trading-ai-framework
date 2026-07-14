from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.agent_decision_log_schemas import (
    AgentDecisionLogResponse,
    PaginatedAgentDecisionLogResponse,
)
from app.core.errors import NotFoundAppError
from app.persistence.database import get_session
from app.persistence.models import ExecutionStepModel
from app.persistence.repositories import AgentDecisionLogRepository, ExperimentRepository

router = APIRouter(prefix="/experiments", tags=["agent-decision-logs"])


def _ensure_experiment_exists(session: Session, experiment_id: int) -> None:
    if ExperimentRepository(session).get_by_id(experiment_id) is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )


@router.get(
    "/{experiment_id}/agent-decision-logs",
    response_model=PaginatedAgentDecisionLogResponse,
)
def list_experiment_agent_decision_logs(
    experiment_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PaginatedAgentDecisionLogResponse:
    _ensure_experiment_exists(session, experiment_id)
    repository = AgentDecisionLogRepository(session)
    items = repository.list_by_experiment_paginated(experiment_id, limit, offset)
    step_ids = {item.execution_step_id for item in items}
    steps = (
        {
            step.id: step
            for step in session.query(ExecutionStepModel)
            .filter(ExecutionStepModel.id.in_(step_ids))
            .all()
        }
        if step_ids
        else {}
    )
    responses = []
    for item in items:
        payload = AgentDecisionLogResponse.model_validate(item).model_dump(
            by_alias=False
        )
        step = steps.get(item.execution_step_id)
        payload["trigger_type"] = step.trigger_type if step is not None else None
        payload["execution_step_sequence_number"] = (
            step.sequence_number if step is not None else None
        )
        payload["execution_step_status"] = step.status if step is not None else None
        payload["scheduled_for"] = step.scheduled_for if step is not None else None
        payload["started_at"] = step.started_at if step is not None else None
        payload["completed_at"] = step.completed_at if step is not None else None
        payload["error_message"] = step.error_message if step is not None else None
        responses.append(AgentDecisionLogResponse.model_validate(payload))
    return PaginatedAgentDecisionLogResponse(
        items=responses,
        limit=limit,
        offset=offset,
        total=repository.count_by_experiment(experiment_id),
    )
