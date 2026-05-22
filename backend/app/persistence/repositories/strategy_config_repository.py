from sqlalchemy import select

from app.persistence.models import StrategyConfigModel
from app.persistence.repositories.base import BaseRepository


class StrategyConfigRepository(BaseRepository[StrategyConfigModel]):
    model = StrategyConfigModel

    def get_by_experiment_id(self, experiment_id: int) -> StrategyConfigModel | None:
        statement = select(self.model).where(self.model.experiment_id == experiment_id)
        return self.session.scalar(statement)
