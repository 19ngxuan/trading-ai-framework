from sqlalchemy import select

from app.persistence.models import RiskCheckModel
from app.persistence.repositories.base import BaseRepository


class RiskCheckRepository(BaseRepository[RiskCheckModel]):
    model = RiskCheckModel

    def list_by_experiment(self, experiment_id: int) -> list[RiskCheckModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.created_at, self.model.id)
        )
        return list(self.session.scalars(statement))
