from sqlalchemy import func, select

from app.persistence.models import TradeModel
from app.persistence.repositories.base import BaseRepository


class TradeRepository(BaseRepository[TradeModel]):
    model = TradeModel

    def count_by_experiment(self, experiment_id: int) -> int:
        statement = select(func.count(self.model.id)).where(
            self.model.experiment_id == experiment_id
        )
        return int(self.session.scalar(statement) or 0)

    def list_by_experiment(self, experiment_id: int) -> list[TradeModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.timestamp, self.model.id)
        )
        return list(self.session.scalars(statement))

    def latest_by_experiment(self, experiment_id: int) -> TradeModel | None:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.timestamp.desc(), self.model.id.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def filled_quantity_by_order(self, order_id: int):
        statement = select(func.coalesce(func.sum(self.model.quantity), 0)).where(
            self.model.order_id == order_id
        )
        return self.session.scalar(statement)
