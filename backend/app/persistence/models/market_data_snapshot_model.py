from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class MarketDataSnapshotModel(Base):
    __tablename__ = "market_data_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False, unique=True
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    open: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    high: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    low: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    close: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    moving_average: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    rsi: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    raw_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_market_data_snapshots_experiment_id", "experiment_id"),
        Index("ix_market_data_snapshots_execution_step_id", "execution_step_id"),
        Index("ix_market_data_snapshots_symbol", "symbol"),
        Index("ix_market_data_snapshots_timestamp", "timestamp"),
    )
