from sqlalchemy import func, select

from app.domain.enums import (
    ExperimentMode,
    ExperimentStatus,
    StrategyType,
    TradingFrequency,
)
from app.persistence.models import ExperimentModel
from app.persistence.repositories.base import BaseRepository


class ExperimentRepository(BaseRepository[ExperimentModel]):
    model = ExperimentModel

    def get_by_id(self, experiment_id: int) -> ExperimentModel | None:
        return self.get(experiment_id)

    def list_filtered(
        self,
        status: ExperimentStatus | None,
        strategy_type: StrategyType | None,
        mode: ExperimentMode | None,
        limit: int,
        offset: int,
    ) -> list[ExperimentModel]:
        statement = select(self.model)
        if status is not None:
            statement = statement.where(self.model.status == status)
        if strategy_type is not None:
            statement = statement.where(self.model.strategy_type == strategy_type)
        if mode is not None:
            statement = statement.where(self.model.mode == mode)

        statement = statement.order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(statement))

    def count_filtered(
        self,
        status: ExperimentStatus | None,
        strategy_type: StrategyType | None,
        mode: ExperimentMode | None,
    ) -> int:
        statement = select(func.count(self.model.id))
        if status is not None:
            statement = statement.where(self.model.status == status)
        if strategy_type is not None:
            statement = statement.where(self.model.strategy_type == strategy_type)
        if mode is not None:
            statement = statement.where(self.model.mode == mode)
        return int(self.session.scalar(statement) or 0)

    def list_scheduler_eligible_experiment_ids(self) -> list[int]:
        statement = (
            select(self.model.id)
            .where(
                self.model.status == ExperimentStatus.RUNNING,
                self.model.mode == ExperimentMode.HISTORICAL_SIMULATION,
                self.model.trading_frequency == TradingFrequency.DAILY,
                self.model.strategy_type.in_(
                    [StrategyType.BUY_AND_HOLD, StrategyType.MOVING_AVERAGE]
                ),
            )
            .order_by(self.model.id.asc())
        )
        return list(self.session.scalars(statement))
