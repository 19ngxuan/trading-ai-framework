from sqlalchemy import select

from app.persistence.models import PortfolioSnapshotModel
from app.persistence.repositories.base import BaseRepository


class PortfolioSnapshotRepository(BaseRepository[PortfolioSnapshotModel]):
    model = PortfolioSnapshotModel

    def list_by_experiment(self, experiment_id: int) -> list[PortfolioSnapshotModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.timestamp, self.model.id)
        )
        return list(self.session.scalars(statement))
