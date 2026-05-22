from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import (
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    TradingFrequency,
)
from app.persistence.database import Base
from app.persistence.models.types import (
    experiment_mode_enum,
    experiment_status_enum,
    fee_model_type_enum,
    strategy_type_enum,
    trading_frequency_enum,
)


class ExperimentModel(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[ExperimentMode] = mapped_column(experiment_mode_enum, nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(
        strategy_type_enum, nullable=False
    )
    asset_symbol: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        experiment_status_enum, nullable=False
    )
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    trading_frequency: Mapped[TradingFrequency] = mapped_column(
        trading_frequency_enum, nullable=False
    )
    fee_model_type: Mapped[FeeModelType] = mapped_column(
        fee_model_type_enum, nullable=False
    )
    fee_value: Mapped[Decimal] = mapped_column(
        Numeric(19, 8), nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_experiments_asset_symbol", "asset_symbol"),
        Index("ix_experiments_strategy_type", "strategy_type"),
        Index("ix_experiments_status", "status"),
        Index("ix_experiments_mode", "mode"),
        Index("ix_experiments_created_at", "created_at"),
    )
