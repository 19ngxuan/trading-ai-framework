from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks

from app.core.config import get_settings
from app.api.schemas.experiment_schemas import (
    CreateExperimentRequest,
    ExperimentActionResponse,
    ExperimentDetailResponse,
    ExperimentResponse,
    ExperimentSummaryResponse,
    PaginatedExperimentSummaryResponse,
    PortfolioResponse,
    StrategyConfigResponse,
)
from app.api.schemas.metrics_schemas import MetricSnapshotResponse, TradeSummaryResponse
from app.api.schemas.options_schemas import OptionsResponse
from app.core.errors import InvalidExperimentConfigurationAppError, NotFoundAppError
from app.domain.enums import (
    AgentMode,
    EventLevel,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    OrderStatus,
    StrategyType,
    SystemEventType,
    TradingFrequency,
)
from app.modules.execution.orchestrator import (
    HistoricalBuyAndHoldOrchestrator,
    HistoricalMovingAverageOrchestrator,
    HistoricalOpeningRangeBreakoutOrchestrator,
)
from app.modules.execution.position_sizing import ALL_IN, parse_position_sizing_value
from app.modules.experiments.status_machine import validate_transition
from app.modules.experiments.validators import validate_create_experiment_request
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExperimentModel,
    PortfolioModel,
    StrategyConfigModel,
    SystemEventLogModel,
    MetricSnapshotModel,
    TradeModel,
)
from app.persistence.repositories import (
    ExperimentRepository,
    MetricSnapshotRepository,
    PortfolioRepository,
    StrategyConfigRepository,
    SystemEventLogRepository,
    TradeRepository,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_experiment_response(model: ExperimentModel) -> ExperimentResponse:
    return ExperimentResponse.model_validate(model)


def _to_portfolio_response(model: PortfolioModel) -> PortfolioResponse:
    return PortfolioResponse.model_validate(model)


def _to_strategy_config_response(model: StrategyConfigModel) -> StrategyConfigResponse:
    response = StrategyConfigResponse.model_validate(model)
    response.position_sizing_value = parse_position_sizing_value(model.parameters_json)
    return response


def _strategy_parameters_json(request: CreateExperimentRequest) -> dict[str, Any] | None:
    parameters_json = dict(request.strategy_config.parameters_json or {})
    sizing_type = request.strategy_config.position_sizing_type or ALL_IN
    if sizing_type == ALL_IN:
        parameters_json.pop("positionSizingValue", None)
    elif request.strategy_config.position_sizing_value is not None:
        value = request.strategy_config.position_sizing_value
        if value == value.to_integral_value():
            parameters_json["positionSizingValue"] = int(value)
        else:
            parameters_json["positionSizingValue"] = float(value)
    return parameters_json or None


def _to_metric_snapshot_response(
    model: MetricSnapshotModel | None,
) -> MetricSnapshotResponse | None:
    if model is None:
        return None
    return MetricSnapshotResponse.model_validate(model)


def _to_trade_summary_response(model: TradeModel | None) -> TradeSummaryResponse | None:
    if model is None:
        return None
    return TradeSummaryResponse.model_validate(model)


def _build_summary(
    experiment: ExperimentModel,
    portfolio: PortfolioModel | None,
    latest_metric: MetricSnapshotModel | None,
    latest_trade: TradeModel | None,
) -> ExperimentSummaryResponse:
    return ExperimentSummaryResponse(
        id=experiment.id,
        name=experiment.name,
        mode=experiment.mode,
        strategyType=experiment.strategy_type,
        assetSymbol=experiment.asset_symbol,
        status=experiment.status,
        currentPortfolioValue=portfolio.current_portfolio_value if portfolio else None,
        totalReturn=latest_metric.total_return if latest_metric else None,
        profitLoss=latest_metric.profit_loss if latest_metric else None,
        numberOfTrades=latest_metric.number_of_trades if latest_metric else None,
        maxDrawdown=latest_metric.max_drawdown if latest_metric else None,
        lastTrade=_to_trade_summary_response(latest_trade),
        latestAgentDecisions=[],
    )


class ExperimentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.experiment_repository = ExperimentRepository(session)
        self.portfolio_repository = PortfolioRepository(session)
        self.strategy_config_repository = StrategyConfigRepository(session)
        self.event_repository = SystemEventLogRepository(session)
        self.metric_snapshot_repository = MetricSnapshotRepository(session)
        self.trade_repository = TradeRepository(session)

    def create_experiment(self, request: CreateExperimentRequest) -> dict[str, Any]:
        validate_create_experiment_request(request)
        now = _utcnow()

        experiment = ExperimentModel(
            name=request.name,
            mode=request.mode,
            strategy_type=request.strategy_type,
            asset_symbol=request.asset_symbol,
            status=ExperimentStatus.CREATED,
            initial_capital=request.initial_capital,
            start_date=request.start_date,
            end_date=request.end_date,
            trading_frequency=request.trading_frequency,
            fee_model_type=request.fee_model_type,
            fee_value=request.fee_value,
            created_at=now,
            updated_at=now,
        )

        try:
            self.experiment_repository.add(experiment)
            self.session.flush()

            strategy_config = StrategyConfigModel(
                experiment_id=experiment.id,
                strategy_type=request.strategy_type,
                strategy_version=request.strategy_config.strategy_version,
                moving_average_window=request.strategy_config.moving_average_window,
                position_sizing_type=request.strategy_config.position_sizing_type,
                agent_mode=request.strategy_config.agent_mode,
                model_name=request.strategy_config.model_name,
                confidence_threshold=request.strategy_config.confidence_threshold,
                parameters_json=_strategy_parameters_json(request),
                created_at=now,
                updated_at=now,
            )
            self.strategy_config_repository.add(strategy_config)

            initial_capital = request.initial_capital.quantize(Decimal("0.0001"))
            portfolio = PortfolioModel(
                experiment_id=experiment.id,
                cash=initial_capital,
                position_symbol=None,
                position_quantity=Decimal("0"),
                current_price=None,
                current_position_value=Decimal("0.0000"),
                current_portfolio_value=initial_capital,
                updated_at=now,
            )
            self.portfolio_repository.add(portfolio)

            self.event_repository.add(
                SystemEventLogModel(
                    execution_step_id=None,
                    experiment_id=experiment.id,
                    timestamp=now,
                    level=EventLevel.INFO,
                    event_type=SystemEventType.EXPERIMENT_CREATED,
                    message="Experiment created.",
                    details_json={"experimentId": experiment.id},
                    created_at=now,
                )
            )

            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return {
            "experiment": _to_experiment_response(experiment),
            "portfolio": _to_portfolio_response(portfolio),
        }

    def list_experiments(
        self,
        status: ExperimentStatus | None,
        strategy_type: StrategyType | None,
        mode: ExperimentMode | None,
        limit: int,
        offset: int,
    ) -> PaginatedExperimentSummaryResponse:
        experiments = self.experiment_repository.list_filtered(
            status=status,
            strategy_type=strategy_type,
            mode=mode,
            limit=limit,
            offset=offset,
        )
        total = self.experiment_repository.count_filtered(
            status=status,
            strategy_type=strategy_type,
            mode=mode,
        )

        portfolios = self.portfolio_repository.get_by_experiment_ids(
            [experiment.id for experiment in experiments]
        )
        portfolios_by_experiment_id = {p.experiment_id: p for p in portfolios}
        items = [
            _build_summary(
                experiment,
                portfolios_by_experiment_id.get(experiment.id),
                self.metric_snapshot_repository.latest_by_experiment(experiment.id),
                self.trade_repository.latest_by_experiment(experiment.id),
            )
            for experiment in experiments
        ]

        return PaginatedExperimentSummaryResponse(
            items=items,
            limit=limit,
            offset=offset,
            total=total,
        )

    def get_experiment_detail(self, experiment_id: int) -> ExperimentDetailResponse:
        experiment = self.experiment_repository.get_by_id(experiment_id)
        if experiment is None:
            raise NotFoundAppError(
                "Experiment was not found.",
                details={"experimentId": experiment_id},
            )

        strategy_config = self.strategy_config_repository.get_by_experiment_id(
            experiment_id
        )
        portfolio = self.portfolio_repository.get_by_experiment_id(experiment_id)
        if strategy_config is None or portfolio is None:
            raise NotFoundAppError(
                "Experiment dependencies were not found.",
                details={"experimentId": experiment_id},
            )

        return ExperimentDetailResponse(
            experiment=_to_experiment_response(experiment),
            strategyConfig=_to_strategy_config_response(strategy_config),
            portfolio=_to_portfolio_response(portfolio),
            latestMetrics=_to_metric_snapshot_response(
                self.metric_snapshot_repository.latest_by_experiment(experiment_id)
            ),
            latestAgentDecisions=[],
        )

    def apply_lifecycle_action(self, experiment_id: int, action: str) -> ExperimentActionResponse:
        experiment = self.experiment_repository.get_by_id(experiment_id)
        if experiment is None:
            raise NotFoundAppError(
                "Experiment was not found.",
                details={"experimentId": experiment_id},
            )

        next_status = validate_transition(action, experiment.status)
        now = _utcnow()
        experiment.status = next_status
        experiment.updated_at = now

        event_map: dict[str, SystemEventType] = {
            "start": SystemEventType.EXPERIMENT_STARTED,
            "pause": SystemEventType.EXPERIMENT_PAUSED,
            "resume": SystemEventType.EXPERIMENT_RESUMED,
            "stop": SystemEventType.EXPERIMENT_STOPPED,
        }
        message_map = {
            "start": "Experiment started.",
            "pause": "Experiment paused.",
            "resume": "Experiment resumed.",
            "stop": "Experiment stopped.",
        }

        try:
            self.event_repository.add(
                SystemEventLogModel(
                    execution_step_id=None,
                    experiment_id=experiment.id,
                    timestamp=now,
                    level=EventLevel.INFO,
                    event_type=event_map[action],
                    message=message_map[action],
                    details_json={"experimentId": experiment.id, "status": next_status.value},
                    created_at=now,
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        response_message = None
        if action == "start":
            response_message = "Experiment start accepted."
        elif action == "resume":
            response_message = "Experiment resumed."

        return ExperimentActionResponse(
            experimentId=experiment.id,
            status=next_status,
            message=response_message,
        )

    def start_experiment(
        self,
        experiment_id: int,
        background_tasks: BackgroundTasks | None = None,
    ) -> ExperimentActionResponse:
        experiment = self.experiment_repository.get_by_id(experiment_id)
        if experiment is None:
            raise NotFoundAppError(
                "Experiment was not found.",
                details={"experimentId": experiment_id},
            )
        if (
            experiment.mode is ExperimentMode.HISTORICAL_SIMULATION
            and experiment.strategy_type is StrategyType.MOVING_AVERAGE
            and experiment.trading_frequency is not TradingFrequency.DAILY
        ):
            raise InvalidExperimentConfigurationAppError(
                "Moving Average historical simulation supports DAILY frequency only.",
                details={
                    "experimentId": experiment_id,
                    "tradingFrequency": experiment.trading_frequency.value,
                },
            )
        if experiment.strategy_type is StrategyType.OPENING_RANGE_BREAKOUT:
            if (
                experiment.mode
                not in {
                    ExperimentMode.HISTORICAL_SIMULATION,
                    ExperimentMode.PAPER_TRADING,
                }
                or experiment.trading_frequency is not TradingFrequency.INTRADAY_5_MIN
                or experiment.asset_symbol != "SPY"
            ):
                raise InvalidExperimentConfigurationAppError(
                    "Opening Range Breakout supports HISTORICAL_SIMULATION or "
                    "PAPER_TRADING, INTRADAY_5_MIN, SPY only.",
                    details={
                        "experimentId": experiment_id,
                        "mode": experiment.mode.value,
                        "tradingFrequency": experiment.trading_frequency.value,
                        "assetSymbol": experiment.asset_symbol,
                    },
                )

        response = self.apply_lifecycle_action(experiment_id, "start")
        experiment = self.experiment_repository.get_by_id(experiment_id)
        if (
            experiment is not None
            and experiment.mode is ExperimentMode.HISTORICAL_SIMULATION
            and experiment.strategy_type is StrategyType.BUY_AND_HOLD
            and background_tasks is not None
        ):
            background_tasks.add_task(run_buy_and_hold_historical_simulation, experiment_id)
        elif (
            experiment is not None
            and experiment.mode is ExperimentMode.HISTORICAL_SIMULATION
            and experiment.strategy_type is StrategyType.MOVING_AVERAGE
            and background_tasks is not None
        ):
            background_tasks.add_task(run_moving_average_historical_simulation, experiment_id)
        elif (
            experiment is not None
            and experiment.mode is ExperimentMode.HISTORICAL_SIMULATION
            and experiment.strategy_type is StrategyType.OPENING_RANGE_BREAKOUT
            and experiment.trading_frequency is TradingFrequency.INTRADAY_5_MIN
            and background_tasks is not None
        ):
            background_tasks.add_task(
                run_opening_range_breakout_historical_simulation,
                experiment_id,
            )
        return response

    def get_options(self) -> OptionsResponse:
        settings = get_settings()
        strategies = list(StrategyType)
        trading_frequencies = list(TradingFrequency)
        if not settings.paper_trading_test_mode_enabled:
            strategies = [
                strategy
                for strategy in strategies
                if strategy is not StrategyType.PAPER_TRADING_SMOKE_TEST
            ]
            trading_frequencies = [
                frequency
                for frequency in trading_frequencies
                if frequency is not TradingFrequency.TEST_1_MIN
            ]
        return OptionsResponse(
            assets=["SPY"],
            modes=list(ExperimentMode),
            strategies=strategies,
            experimentStatuses=list(ExperimentStatus),
            tradingFrequencies=trading_frequencies,
            feeModelTypes=list(FeeModelType),
            agentModes=list(AgentMode),
            orderStatuses=list(OrderStatus),
            scadsaiLlmEnabled=settings.scadsai_llm_enabled,
            scadsaiAllowedModels=settings.scadsai_allowed_model_list,
            scadsaiDefaultModel=settings.scadsai_default_model,
        )


def run_buy_and_hold_historical_simulation(experiment_id: int) -> None:
    orchestrator = HistoricalBuyAndHoldOrchestrator(
        session_factory=create_session_factory()
    )
    orchestrator.run(experiment_id)


def run_moving_average_historical_simulation(experiment_id: int) -> None:
    orchestrator = HistoricalMovingAverageOrchestrator(
        session_factory=create_session_factory()
    )
    orchestrator.run(experiment_id)


def run_opening_range_breakout_historical_simulation(experiment_id: int) -> None:
    orchestrator = HistoricalOpeningRangeBreakoutOrchestrator(
        session_factory=create_session_factory()
    )
    orchestrator.run(experiment_id)
