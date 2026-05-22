from sqlalchemy import func, select

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
