from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ImpactDirection
from app.persistence.database import Base
from app.persistence.models.types import impact_direction_enum


class EventAssetImpactModel(Base):
    __tablename__ = "event_asset_impacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("news_events.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    impact_direction: Mapped[ImpactDirection] = mapped_column(
        impact_direction_enum, nullable=False
    )
    relevance_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    raw_impact_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "symbol",
            name="uq_event_asset_impacts_event_symbol",
        ),
        Index("ix_event_asset_impacts_event_id", "event_id"),
        Index("ix_event_asset_impacts_symbol", "symbol"),
        Index("ix_event_asset_impacts_relevance_score", "relevance_score"),
    )
