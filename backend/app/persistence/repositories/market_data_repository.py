from app.persistence.models import MarketDataSnapshotModel
from app.persistence.repositories.base import BaseRepository


class MarketDataSnapshotRepository(BaseRepository[MarketDataSnapshotModel]):
    model = MarketDataSnapshotModel
