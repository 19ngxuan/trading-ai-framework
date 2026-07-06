from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import NewsEventSeverity, NewsEventType
from app.persistence.database import Base
from app.persistence.models.types import news_event_severity_enum, news_event_type_enum


class NewsEventModel(Base):
    __tablename__ = "news_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    external_event_id: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[NewsEventType] = mapped_column(
        news_event_type_enum, nullable=False
    )
    severity: Mapped[NewsEventSeverity] = mapped_column(
        news_event_severity_enum, nullable=False
    )
    affected_symbols_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_event_id",
            name="uq_news_events_provider_external_event_id",
        ),
        Index("ix_news_events_timestamp", "timestamp"),
        Index("ix_news_events_event_type", "event_type"),
        Index("ix_news_events_severity", "severity"),
    )
