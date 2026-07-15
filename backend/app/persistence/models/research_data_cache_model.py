from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class ResearchDataCacheModel(Base):
    __tablename__ = "research_data_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    dataset: Mapped[str] = mapped_column(String, nullable=False)
    cache_key: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, nullable=False
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "symbol",
            "dataset",
            "cache_key",
            name="uq_research_data_cache_provider_symbol_dataset_key",
        ),
        Index("ix_research_data_cache_provider_symbol", "provider", "symbol"),
        Index("ix_research_data_cache_dataset", "dataset"),
        Index("ix_research_data_cache_expires_at", "expires_at"),
    )
