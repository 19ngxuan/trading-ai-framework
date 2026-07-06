from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    EventDecisionStatus,
    ImpactDirection,
    NewsEventSeverity,
    NewsEventType,
)


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EventAssetImpactResponse(CamelModel):
    id: int
    event_id: int = Field(alias="eventId")
    symbol: str
    impact_direction: ImpactDirection = Field(alias="impactDirection")
    relevance_score: Decimal = Field(alias="relevanceScore")
    rationale: str | None
    raw_impact_json: dict[str, Any] | None = Field(alias="rawImpactJson")
    created_at: datetime = Field(alias="createdAt")


class NewsEventResponse(CamelModel):
    id: int
    provider: str
    external_event_id: str = Field(alias="externalEventId")
    timestamp: datetime
    updated_at: datetime | None = Field(alias="updatedAt")
    headline: str
    source: str | None
    url: str | None
    summary: str | None
    event_type: NewsEventType = Field(alias="eventType")
    severity: NewsEventSeverity
    affected_symbols_json: list[str] = Field(alias="affectedSymbols")
    raw_payload_json: dict[str, Any] | None = Field(alias="rawPayloadJson")
    first_seen_at: datetime = Field(alias="firstSeenAt")
    last_seen_at: datetime = Field(alias="lastSeenAt")
    created_at: datetime = Field(alias="createdAt")


class NewsEventDetailResponse(NewsEventResponse):
    impacts: list[EventAssetImpactResponse]


class PaginatedNewsEventResponse(CamelModel):
    items: list[NewsEventResponse]
    limit: int
    offset: int
    total: int


class EventDecisionResponse(CamelModel):
    id: int
    event_id: int = Field(alias="eventId")
    experiment_id: int = Field(alias="experimentId")
    execution_step_id: int | None = Field(alias="executionStepId")
    trading_decision_id: int | None = Field(alias="tradingDecisionId")
    status: EventDecisionStatus
    reason: str | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class PaginatedEventDecisionResponse(CamelModel):
    items: list[EventDecisionResponse]
    limit: int
    offset: int
    total: int
