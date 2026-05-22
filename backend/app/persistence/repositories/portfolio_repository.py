from sqlalchemy import select

from app.persistence.models import PortfolioModel
from app.persistence.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[PortfolioModel]):
    model = PortfolioModel

    def get_by_experiment_id(self, experiment_id: int) -> PortfolioModel | None:
        statement = select(self.model).where(self.model.experiment_id == experiment_id)
        return self.session.scalar(statement)

    def get_by_experiment_ids(self, experiment_ids: list[int]) -> list[PortfolioModel]:
        if not experiment_ids:
            return []
        statement = select(self.model).where(self.model.experiment_id.in_(experiment_ids))
        return list(self.session.scalars(statement))
