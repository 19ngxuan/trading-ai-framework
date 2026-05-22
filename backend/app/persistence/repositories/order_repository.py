from sqlalchemy import select

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
