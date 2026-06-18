from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import AgentMode, StrategyType
from app.persistence.database import Base
from app.persistence.models.types import agent_mode_enum, strategy_type_enum


class StrategyConfigModel(Base):
    __tablename__ = "strategy_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False, unique=True
    )
    strategy_type: Mapped[StrategyType] = mapped_column(
        strategy_type_enum, nullable=False
    )
    moving_average_window: Mapped[int | None] = mapped_column(Integer)
    agent_mode: Mapped[AgentMode | None] = mapped_column(agent_mode_enum)
    model_name: Mapped[str | None] = mapped_column(String)
    confidence_threshold: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    parameters_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_strategy_configs_strategy_type", "strategy_type"),
        Index("ix_strategy_configs_agent_mode", "agent_mode"),
    )
