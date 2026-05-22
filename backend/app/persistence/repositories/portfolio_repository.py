from app.persistence.models import PortfolioModel
from app.persistence.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[PortfolioModel]):
    model = PortfolioModel
