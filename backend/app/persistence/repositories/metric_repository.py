from sqlalchemy import select

from app.persistence.models import MetricSnapshotModel
from app.persistence.repositories.base import BaseRepository


class MetricSnapshotRepository(BaseRepository[MetricSnapshotModel]):
    model = MetricSnapshotModel

    def list_by_experiment(self, experiment_id: int) -> list[MetricSnapshotModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.timestamp, self.model.id)
        )
        return list(self.session.scalars(statement))
