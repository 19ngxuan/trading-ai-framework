from app.persistence.models import TradingDecisionModel
from app.persistence.repositories.base import BaseRepository


class TradingDecisionRepository(BaseRepository[TradingDecisionModel]):
    model = TradingDecisionModel
