from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class PortfolioSnapshotModel(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False, unique=True
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    position_symbol: Mapped[str | None] = mapped_column(String)
    position_quantity: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    position_market_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    total_portfolio_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_portfolio_snapshots_experiment_id", "experiment_id"),
        Index("ix_portfolio_snapshots_execution_step_id", "execution_step_id"),
        Index("ix_portfolio_snapshots_timestamp", "timestamp"),
    )
