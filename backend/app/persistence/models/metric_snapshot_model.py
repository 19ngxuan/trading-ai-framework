from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class MetricSnapshotModel(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False, unique=True
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_return: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    profit_loss: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    number_of_trades: Mapped[int | None] = mapped_column(Integer)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    buy_and_hold_return: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    difference_to_buy_and_hold: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_metric_snapshots_experiment_id", "experiment_id"),
        Index("ix_metric_snapshots_execution_step_id", "execution_step_id"),
        Index("ix_metric_snapshots_timestamp", "timestamp"),
    )
