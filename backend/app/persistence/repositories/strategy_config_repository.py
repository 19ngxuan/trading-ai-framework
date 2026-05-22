from app.persistence.models import StrategyConfigModel
from app.persistence.repositories.base import BaseRepository


class StrategyConfigRepository(BaseRepository[StrategyConfigModel]):
    model = StrategyConfigModel
