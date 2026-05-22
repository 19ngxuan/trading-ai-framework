from app.persistence.models import MetricSnapshotModel
from app.persistence.repositories.base import BaseRepository


class MetricSnapshotRepository(BaseRepository[MetricSnapshotModel]):
    model = MetricSnapshotModel
