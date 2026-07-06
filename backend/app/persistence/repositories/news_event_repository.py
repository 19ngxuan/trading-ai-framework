from sqlalchemy import select

from app.domain.enums import EventDecisionStatus, NewsEventSeverity, NewsEventType
from app.persistence.models import (
    EventAssetImpactModel,
    EventDecisionModel,
    NewsEventModel,
)
from app.persistence.repositories.base import BaseRepository


class NewsEventRepository(BaseRepository[NewsEventModel]):
    model = NewsEventModel

    def get_by_provider_external_id(
        self, provider: str, external_event_id: str
    ) -> NewsEventModel | None:
        statement = select(self.model).where(
            self.model.provider == provider,
            self.model.external_event_id == external_event_id,
        )
        return self.session.scalar(statement)

    def list_filtered(
        self,
        *,
        symbol: str | None = None,
        event_type: NewsEventType | None = None,
        severity: NewsEventSeverity | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NewsEventModel]:
        statement = select(self.model)
        if symbol is not None:
            statement = statement.where(
                self.model.affected_symbols_json.op("?")(symbol.upper())
            )
        if event_type is not None:
            statement = statement.where(self.model.event_type == event_type)
        if severity is not None:
            statement = statement.where(self.model.severity == severity)
        statement = (
            statement.order_by(self.model.timestamp.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))


class EventAssetImpactRepository(BaseRepository[EventAssetImpactModel]):
    model = EventAssetImpactModel

    def get_by_event_symbol(
        self, event_id: int, symbol: str
    ) -> EventAssetImpactModel | None:
        statement = select(self.model).where(
            self.model.event_id == event_id,
            self.model.symbol == symbol.upper(),
        )
        return self.session.scalar(statement)

    def list_by_event(self, event_id: int) -> list[EventAssetImpactModel]:
        statement = (
            select(self.model)
            .where(self.model.event_id == event_id)
            .order_by(self.model.relevance_score.desc(), self.model.id.asc())
        )
        return list(self.session.scalars(statement))


class EventDecisionRepository(BaseRepository[EventDecisionModel]):
    model = EventDecisionModel

    def get_by_event_experiment(
        self, event_id: int, experiment_id: int
    ) -> EventDecisionModel | None:
        statement = select(self.model).where(
            self.model.event_id == event_id,
            self.model.experiment_id == experiment_id,
        )
        return self.session.scalar(statement)

    def list_by_experiment(
        self,
        experiment_id: int,
        *,
        status: EventDecisionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EventDecisionModel]:
        statement = select(self.model).where(self.model.experiment_id == experiment_id)
        if status is not None:
            statement = statement.where(self.model.status == status)
        statement = (
            statement.order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))
