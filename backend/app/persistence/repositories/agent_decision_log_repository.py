from app.persistence.models import AgentDecisionLogModel
from app.persistence.repositories.base import BaseRepository


class AgentDecisionLogRepository(BaseRepository[AgentDecisionLogModel]):
    model = AgentDecisionLogModel
