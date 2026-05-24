from sqlalchemy import func, select

from app.domain.enums import EventLevel, SystemEventType
from app.persistence.models import SystemEventLogModel
from app.persistence.repositories.base import BaseRepository


class SystemEventLogRepository(BaseRepository[SystemEventLogModel]):
    model = SystemEventLogModel

    def list_filtered(
        self,
        *,
        experiment_id: int | None,
        level: EventLevel | None,
        event_type: SystemEventType | None,
        limit: int,
        offset: int,
    ) -> list[SystemEventLogModel]:
        statement = self._filtered_statement(experiment_id, level, event_type)
        statement = (
            statement.order_by(self.model.timestamp.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def count_filtered(
        self,
        *,
        experiment_id: int | None,
        level: EventLevel | None,
        event_type: SystemEventType | None,
    ) -> int:
        statement = select(func.count(self.model.id))
        if experiment_id is not None:
            statement = statement.where(self.model.experiment_id == experiment_id)
        if level is not None:
            statement = statement.where(self.model.level == level)
        if event_type is not None:
            statement = statement.where(self.model.event_type == event_type)
        return int(self.session.scalar(statement) or 0)

    def _filtered_statement(
        self,
        experiment_id: int | None,
        level: EventLevel | None,
        event_type: SystemEventType | None,
    ):
        statement = select(self.model)
        if experiment_id is not None:
            statement = statement.where(self.model.experiment_id == experiment_id)
        if level is not None:
            statement = statement.where(self.model.level == level)
        if event_type is not None:
            statement = statement.where(self.model.event_type == event_type)
        return statement
