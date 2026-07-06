from sqlalchemy import func, select

from app.domain.assets import SPY_SYMBOL
from app.domain.assets import SUPPORTED_EQUITY_SYMBOLS
from app.domain.enums import (
    AgentMode,
    ExperimentMode,
    ExperimentStatus,
    StrategyType,
    TradingFrequency,
)
from app.persistence.models import ExperimentModel
from app.persistence.models import StrategyConfigModel
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

    def list_by_ids(self, experiment_ids: list[int]) -> list[ExperimentModel]:
        if not experiment_ids:
            return []
        statement = select(self.model).where(self.model.id.in_(experiment_ids))
        return list(self.session.scalars(statement))

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

    def list_paper_daily_scheduler_eligible_experiment_ids(self) -> list[int]:
        statement = (
            select(self.model.id)
            .join(
                StrategyConfigModel,
                StrategyConfigModel.experiment_id == self.model.id,
            )
            .where(
                self.model.status == ExperimentStatus.RUNNING,
                self.model.mode == ExperimentMode.PAPER_TRADING,
                self.model.trading_frequency == TradingFrequency.DAILY,
                (
                    self.model.strategy_type.in_(
                        [StrategyType.BUY_AND_HOLD, StrategyType.MOVING_AVERAGE]
                    )
                    | (
                        (self.model.strategy_type == StrategyType.AGENTIC_AI)
                        & (
                            (StrategyConfigModel.agent_mode.is_(None))
                            | (
                                StrategyConfigModel.agent_mode
                                == AgentMode.SINGLE_AGENT
                            )
                            | (
                                StrategyConfigModel.agent_mode
                                == AgentMode.PIPELINE
                            )
                        )
                    )
                ),
                self.model.asset_symbol.in_(SUPPORTED_EQUITY_SYMBOLS),
            )
            .order_by(self.model.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_paper_hourly_ai_scheduler_eligible_experiment_ids(self) -> list[int]:
        statement = (
            select(self.model.id)
            .join(
                StrategyConfigModel,
                StrategyConfigModel.experiment_id == self.model.id,
            )
            .where(
                self.model.status == ExperimentStatus.RUNNING,
                self.model.mode == ExperimentMode.PAPER_TRADING,
                self.model.trading_frequency == TradingFrequency.HOURLY,
                self.model.strategy_type == StrategyType.AGENTIC_AI,
                (
                    StrategyConfigModel.agent_mode.is_(None)
                    | (StrategyConfigModel.agent_mode == AgentMode.SINGLE_AGENT)
                    | (StrategyConfigModel.agent_mode == AgentMode.PIPELINE)
                ),
                self.model.asset_symbol.in_(SUPPORTED_EQUITY_SYMBOLS),
            )
            .order_by(self.model.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_paper_orb_scheduler_eligible_experiment_ids(self) -> list[int]:
        statement = (
            select(self.model.id)
            .where(
                self.model.status == ExperimentStatus.RUNNING,
                self.model.mode == ExperimentMode.PAPER_TRADING,
                self.model.trading_frequency == TradingFrequency.INTRADAY_5_MIN,
                self.model.strategy_type == StrategyType.OPENING_RANGE_BREAKOUT,
                self.model.asset_symbol == SPY_SYMBOL,
            )
            .order_by(self.model.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_paper_smoke_test_scheduler_eligible_experiment_ids(self) -> list[int]:
        statement = (
            select(self.model.id)
            .where(
                self.model.status == ExperimentStatus.RUNNING,
                self.model.mode == ExperimentMode.PAPER_TRADING,
                self.model.trading_frequency == TradingFrequency.TEST_1_MIN,
                self.model.strategy_type == StrategyType.PAPER_TRADING_SMOKE_TEST,
                self.model.asset_symbol == SPY_SYMBOL,
            )
            .order_by(self.model.id.asc())
        )
        return list(self.session.scalars(statement))
