from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import OrderSide
from app.persistence.database import Base
from app.persistence.models.types import order_side_enum


class TradeModel(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[OrderSide] = mapped_column(order_side_enum, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(19, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(19, 8), nullable=False)
    order_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    fee: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    portfolio_value_after_trade: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_trades_experiment_id", "experiment_id"),
        Index("ix_trades_execution_step_id", "execution_step_id"),
        Index("ix_trades_order_id", "order_id"),
        Index("ix_trades_symbol", "symbol"),
        Index("ix_trades_timestamp", "timestamp"),
    )
