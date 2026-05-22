from app.persistence.models import PortfolioSnapshotModel
from app.persistence.repositories.base import BaseRepository


class PortfolioSnapshotRepository(BaseRepository[PortfolioSnapshotModel]):
    model = PortfolioSnapshotModel
