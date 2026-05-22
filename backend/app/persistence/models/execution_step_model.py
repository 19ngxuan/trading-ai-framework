from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ExecutionStepStatus, TriggerType
from app.persistence.database import Base
from app.persistence.models.types import execution_step_status_enum, trigger_type_enum


class ExecutionStepModel(Base):
    __tablename__ = "execution_steps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[ExecutionStepStatus] = mapped_column(
        execution_step_status_enum, nullable=False
    )
    trigger_type: Mapped[TriggerType] = mapped_column(trigger_type_enum, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "sequence_number",
            name="uq_execution_steps_experiment_sequence",
        ),
        Index("ix_execution_steps_experiment_id", "experiment_id"),
        Index("ix_execution_steps_sequence_number", "sequence_number"),
        Index("ix_execution_steps_status", "status"),
        Index("ix_execution_steps_scheduled_for", "scheduled_for"),
        Index("ix_execution_steps_created_at", "created_at"),
    )
