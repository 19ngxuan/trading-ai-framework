from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import AgentMode, AgentStepName, ParsingStatus
from app.persistence.database import Base
from app.persistence.models.types import (
    agent_mode_enum,
    agent_step_name_enum,
    parsing_status_enum,
)


class AgentDecisionLogModel(Base):
    __tablename__ = "agent_decision_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    trading_decision_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("trading_decisions.id")
    )
    agent_mode: Mapped[AgentMode] = mapped_column(agent_mode_enum, nullable=False)
    agent_step_name: Mapped[AgentStepName] = mapped_column(
        agent_step_name_enum, nullable=False
    )
    agent_name: Mapped[str | None] = mapped_column(String)
    prompt_version: Mapped[str | None] = mapped_column(String)
    model_name: Mapped[str | None] = mapped_column(String)
    model_version: Mapped[str | None] = mapped_column(String)
    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    raw_output_text: Mapped[str | None] = mapped_column(Text)
    parsed_output_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        parsing_status_enum, nullable=False
    )
    repair_prompt_text: Mapped[str | None] = mapped_column(Text)
    repair_raw_output_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_agent_decision_logs_experiment_id", "experiment_id"),
        Index("ix_agent_decision_logs_execution_step_id", "execution_step_id"),
        Index("ix_agent_decision_logs_trading_decision_id", "trading_decision_id"),
        Index("ix_agent_decision_logs_agent_mode", "agent_mode"),
        Index("ix_agent_decision_logs_agent_step_name", "agent_step_name"),
        Index("ix_agent_decision_logs_parsing_status", "parsing_status"),
        Index("ix_agent_decision_logs_created_at", "created_at"),
    )
