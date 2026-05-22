from app.persistence.models import ExperimentModel
from app.persistence.repositories.base import BaseRepository


class ExperimentRepository(BaseRepository[ExperimentModel]):
    model = ExperimentModel

    def get_by_id(self, experiment_id: int) -> ExperimentModel | None:
        return self.get(experiment_id)
