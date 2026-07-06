from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import EventDecisionStatus
from app.persistence.database import Base
from app.persistence.models.types import event_decision_status_enum


class EventDecisionModel(Base):
    __tablename__ = "event_decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("news_events.id"), nullable=False
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    execution_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id")
    )
    trading_decision_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("trading_decisions.id")
    )
    status: Mapped[EventDecisionStatus] = mapped_column(
        event_decision_status_enum, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "experiment_id",
            name="uq_event_decisions_event_experiment",
        ),
        Index("ix_event_decisions_event_id", "event_id"),
        Index("ix_event_decisions_experiment_id", "experiment_id"),
        Index("ix_event_decisions_status", "status"),
    )
