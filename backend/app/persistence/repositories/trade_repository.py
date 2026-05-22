from app.persistence.models import TradeModel
from app.persistence.repositories.base import BaseRepository


class TradeRepository(BaseRepository[TradeModel]):
    model = TradeModel
