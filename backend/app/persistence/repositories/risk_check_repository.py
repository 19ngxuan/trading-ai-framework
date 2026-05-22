from app.persistence.models import RiskCheckModel
from app.persistence.repositories.base import BaseRepository


class RiskCheckRepository(BaseRepository[RiskCheckModel]):
    model = RiskCheckModel
