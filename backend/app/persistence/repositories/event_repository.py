from app.persistence.models import SystemEventLogModel
from app.persistence.repositories.base import BaseRepository


class SystemEventLogRepository(BaseRepository[SystemEventLogModel]):
    model = SystemEventLogModel
