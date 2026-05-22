from app.core.errors import InvalidStatusAppError
from app.domain.enums import ExperimentStatus

LIFECYCLE_TRANSITIONS: dict[str, set[ExperimentStatus]] = {
    "start": {ExperimentStatus.CREATED},
    "pause": {ExperimentStatus.RUNNING},
    "resume": {ExperimentStatus.PAUSED},
    "stop": {ExperimentStatus.RUNNING, ExperimentStatus.PAUSED},
}

TARGET_STATUSES: dict[str, ExperimentStatus] = {
    "start": ExperimentStatus.RUNNING,
    "pause": ExperimentStatus.PAUSED,
    "resume": ExperimentStatus.RUNNING,
    "stop": ExperimentStatus.STOPPED,
}


def validate_transition(action: str, current_status: ExperimentStatus) -> ExperimentStatus:
    allowed_from = LIFECYCLE_TRANSITIONS[action]
    if current_status not in allowed_from:
        action_label = action
        if action == "pause":
            action_label = "paused"
        elif action == "resume":
            action_label = "resumed"
        elif action == "start":
            action_label = "started"
        elif action == "stop":
            action_label = "stopped"
        raise InvalidStatusAppError(
            message=f"Experiment cannot be {action_label} from status {current_status.value}.",
        )
    return TARGET_STATUSES[action]
