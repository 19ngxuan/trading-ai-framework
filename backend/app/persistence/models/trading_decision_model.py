from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import DecisionSourceType, TradeAction
from app.persistence.database import Base
from app.persistence.models.types import decision_source_type_enum, trade_action_enum


class TradingDecisionModel(Base):
    __tablename__ = "trading_decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False, unique=True
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    market_data_snapshot_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("market_data_snapshots.id"), nullable=False
    )
    source_type: Mapped[DecisionSourceType] = mapped_column(
        decision_source_type_enum, nullable=False
    )
    source_name: Mapped[str | None] = mapped_column(String)
    action: Mapped[TradeAction] = mapped_column(trade_action_enum, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    suggested_quantity: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    suggested_notional: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    raw_decision_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_trading_decisions_experiment_id", "experiment_id"),
        Index("ix_trading_decisions_execution_step_id", "execution_step_id"),
        Index(
            "ix_trading_decisions_market_data_snapshot_id", "market_data_snapshot_id"
        ),
        Index("ix_trading_decisions_source_type", "source_type"),
        Index("ix_trading_decisions_action", "action"),
    )
