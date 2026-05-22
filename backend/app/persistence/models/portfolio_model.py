from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class PortfolioModel(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("experiments.id"), nullable=False, unique=True
    )
    cash: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    position_symbol: Mapped[str | None] = mapped_column(String)
    position_quantity: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8))
    current_position_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    current_portfolio_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
