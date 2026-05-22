from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import BrokerName, BrokerSyncStatus
from app.persistence.database import Base
from app.persistence.models.types import broker_name_enum, broker_sync_status_enum


class BrokerSyncLogModel(Base):
    __tablename__ = "broker_sync_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    broker_name: Mapped[BrokerName] = mapped_column(broker_name_enum, nullable=False)
    sync_status: Mapped[BrokerSyncStatus] = mapped_column(
        broker_sync_status_enum, nullable=False
    )
    broker_cash: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    local_cash: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    broker_positions_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    local_positions_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    mismatch_details_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_broker_sync_logs_experiment_id", "experiment_id"),
        Index("ix_broker_sync_logs_execution_step_id", "execution_step_id"),
        Index("ix_broker_sync_logs_broker_name", "broker_name"),
        Index("ix_broker_sync_logs_sync_status", "sync_status"),
        Index("ix_broker_sync_logs_timestamp", "timestamp"),
    )
