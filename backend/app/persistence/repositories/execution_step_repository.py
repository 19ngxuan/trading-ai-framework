from datetime import datetime

from sqlalchemy import func, select

from app.domain.enums import ExecutionStepStatus, TriggerType
from app.persistence.models import ExecutionStepModel
from app.persistence.repositories.base import BaseRepository


class ExecutionStepRepository(BaseRepository[ExecutionStepModel]):
    model = ExecutionStepModel

    def max_sequence_number(self, experiment_id: int) -> int:
        statement = select(func.max(self.model.sequence_number)).where(
            self.model.experiment_id == experiment_id
        )
        return int(self.session.scalar(statement) or 0)

    def list_by_experiment(self, experiment_id: int) -> list[ExecutionStepModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.sequence_number)
        )
        return list(self.session.scalars(statement))

    def count_by_experiment(self, experiment_id: int) -> int:
        statement = select(func.count(self.model.id)).where(
            self.model.experiment_id == experiment_id
        )
        return int(self.session.scalar(statement) or 0)

    def has_running_step(self, experiment_id: int) -> bool:
        statement = (
            select(self.model.id)
            .where(
                self.model.experiment_id == experiment_id,
                self.model.status == ExecutionStepStatus.RUNNING,
            )
            .limit(1)
        )
        return self.session.scalar(statement) is not None

    def has_step_for_scheduled_slot(
        self, experiment_id: int, scheduled_for: datetime
    ) -> bool:
        statement = (
            select(self.model.id)
            .where(
                self.model.experiment_id == experiment_id,
                self.model.trigger_type == TriggerType.SCHEDULED,
                self.model.scheduled_for == scheduled_for,
            )
            .limit(1)
        )
        return self.session.scalar(statement) is not None

    def latest_by_experiment(self, experiment_id: int) -> ExecutionStepModel | None:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(1)
        )
        return self.session.scalar(statement)
