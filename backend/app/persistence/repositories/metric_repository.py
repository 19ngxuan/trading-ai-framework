from sqlalchemy import func, select

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

    def list_by_experiment_paginated(
        self, experiment_id: int, limit: int, offset: int
    ) -> list[MetricSnapshotModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.timestamp, self.model.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def count_by_experiment(self, experiment_id: int) -> int:
        statement = select(func.count(self.model.id)).where(
            self.model.experiment_id == experiment_id
        )
        return int(self.session.scalar(statement) or 0)

    def latest_by_experiment(self, experiment_id: int) -> MetricSnapshotModel | None:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.timestamp.desc(), self.model.id.desc())
            .limit(1)
        )
        return self.session.scalar(statement)
