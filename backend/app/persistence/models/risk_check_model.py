from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import FinalAction
from app.persistence.database import Base
from app.persistence.models.types import final_action_enum


class RiskCheckModel(Base):
    __tablename__ = "risk_checks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False, unique=True
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    trading_decision_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("trading_decisions.id"), nullable=False, unique=True
    )
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    final_action: Mapped[FinalAction] = mapped_column(final_action_enum, nullable=False)
    final_quantity: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    final_notional: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    rules_triggered_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_risk_checks_experiment_id", "experiment_id"),
        Index("ix_risk_checks_execution_step_id", "execution_step_id"),
        Index("ix_risk_checks_trading_decision_id", "trading_decision_id"),
        Index("ix_risk_checks_approved", "approved"),
        Index("ix_risk_checks_final_action", "final_action"),
    )
