from sqlalchemy import select

from app.domain.enums import BrokerName, OrderMode, OrderStatus
from app.persistence.models import OrderModel
from app.persistence.repositories.base import BaseRepository


class OrderRepository(BaseRepository[OrderModel]):
    model = OrderModel

    def list_by_experiment(self, experiment_id: int) -> list[OrderModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.created_at, self.model.id)
        )
        return list(self.session.scalars(statement))

    def list_open_paper_orders(self) -> list[OrderModel]:
        statement = (
            select(self.model)
            .where(
                self.model.mode == OrderMode.PAPER_BROKER,
                self.model.broker_name == BrokerName.ALPACA,
                self.model.status == OrderStatus.SUBMITTED,
                self.model.broker_order_id.is_not(None),
            )
            .order_by(self.model.submitted_at.asc(), self.model.id.asc())
        )
        return list(self.session.scalars(statement))
