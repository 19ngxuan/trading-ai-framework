from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import EventLevel, SystemEventType
from app.persistence.database import Base
from app.persistence.models.types import event_level_enum, system_event_type_enum


class SystemEventLogModel(Base):
    __tablename__ = "system_event_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id")
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    level: Mapped[EventLevel] = mapped_column(event_level_enum, nullable=False)
    event_type: Mapped[SystemEventType] = mapped_column(
        system_event_type_enum, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_system_event_logs_experiment_id", "experiment_id"),
        Index("ix_system_event_logs_execution_step_id", "execution_step_id"),
        Index("ix_system_event_logs_level", "level"),
        Index("ix_system_event_logs_event_type", "event_type"),
        Index("ix_system_event_logs_timestamp", "timestamp"),
    )
