from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import BrokerName, OrderMode, OrderSide, OrderStatus, OrderType
from app.persistence.database import Base
from app.persistence.models.types import (
    broker_name_enum,
    order_mode_enum,
    order_side_enum,
    order_status_enum,
    order_type_enum,
)


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_steps.id"), nullable=False, unique=True
    )
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False
    )
    risk_check_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("risk_checks.id"), nullable=False, unique=True
    )
    mode: Mapped[OrderMode] = mapped_column(order_mode_enum, nullable=False)
    broker_name: Mapped[BrokerName | None] = mapped_column(broker_name_enum)
    broker_order_id: Mapped[str | None] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[OrderSide] = mapped_column(order_side_enum, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(19, 8), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(order_type_enum, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(order_status_enum, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime)
    average_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_orders_experiment_id", "experiment_id"),
        Index("ix_orders_execution_step_id", "execution_step_id"),
        Index("ix_orders_risk_check_id", "risk_check_id"),
        Index("ix_orders_broker_order_id", "broker_order_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_symbol", "symbol"),
    )
