from app.persistence.models import BrokerSyncLogModel
from app.persistence.repositories.base import BaseRepository


class BrokerSyncLogRepository(BaseRepository[BrokerSyncLogModel]):
    model = BrokerSyncLogModel
