from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.enums import ImpactDirection, NewsEventSeverity, NewsEventType


@dataclass(frozen=True)
class NewsArticle:
    provider: str
    external_event_id: str
    timestamp: datetime
    updated_at: datetime | None
    headline: str
    source: str | None
    url: str | None
    summary: str | None
    symbols: tuple[str, ...]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class ClassifiedEvent:
    event_type: NewsEventType
    severity: NewsEventSeverity
    impact_direction: ImpactDirection
    relevance_score: Decimal
    rationale: str
