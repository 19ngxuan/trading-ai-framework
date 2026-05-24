from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.comparison_schemas import (
    CompareExperimentRow,
    CompareExperimentsRequest,
    CompareExperimentsResponse,
)
from app.core.errors import NotFoundAppError, ValidationAppError
from app.persistence.database import get_session
from app.persistence.repositories import (
    ExperimentRepository,
    MetricSnapshotRepository,
    PortfolioRepository,
)

router = APIRouter(prefix="/experiments", tags=["comparison"])


@router.post("/compare", response_model=CompareExperimentsResponse)
def compare_experiments(
    request: CompareExperimentsRequest,
    session: Session = Depends(get_session),
) -> CompareExperimentsResponse:
    _validate_compare_request(request)
    experiment_repository = ExperimentRepository(session)
    experiments = experiment_repository.list_by_ids(request.experiment_ids)
    experiments_by_id = {experiment.id: experiment for experiment in experiments}
    missing_ids = [
        experiment_id
        for experiment_id in request.experiment_ids
        if experiment_id not in experiments_by_id
    ]
    if missing_ids:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": missing_ids[0], "missingExperimentIds": missing_ids},
        )

    portfolio_repository = PortfolioRepository(session)
    metric_repository = MetricSnapshotRepository(session)
    portfolios_by_experiment_id = {
        portfolio.experiment_id: portfolio
        for portfolio in portfolio_repository.get_by_experiment_ids(
            request.experiment_ids
        )
    }
    latest_metrics_by_experiment_id = {
        experiment_id: metric_repository.latest_by_experiment(experiment_id)
        for experiment_id in request.experiment_ids
    }

    benchmark_return = None
    if request.benchmark_experiment_id is not None:
        benchmark_metric = latest_metrics_by_experiment_id.get(
            request.benchmark_experiment_id
        )
        benchmark_return = benchmark_metric.total_return if benchmark_metric else None

    rows = []
    for experiment_id in request.experiment_ids:
        experiment = experiments_by_id[experiment_id]
        portfolio = portfolios_by_experiment_id.get(experiment_id)
        latest_metric = latest_metrics_by_experiment_id[experiment_id]
        total_return = latest_metric.total_return if latest_metric else None
        difference_to_benchmark = (
            total_return - benchmark_return
            if total_return is not None and benchmark_return is not None
            else None
        )
        rows.append(
            CompareExperimentRow(
                experimentId=experiment.id,
                name=experiment.name,
                mode=experiment.mode,
                strategyType=experiment.strategy_type,
                status=experiment.status,
                assetSymbol=experiment.asset_symbol,
                latestPortfolioValue=(
                    portfolio.current_portfolio_value if portfolio else None
                ),
                totalReturn=total_return,
                profitLoss=latest_metric.profit_loss if latest_metric else None,
                numberOfTrades=(
                    latest_metric.number_of_trades if latest_metric else None
                ),
                maxDrawdown=latest_metric.max_drawdown if latest_metric else None,
                benchmarkReturn=benchmark_return,
                differenceToBenchmark=difference_to_benchmark,
            )
        )

    return CompareExperimentsResponse(
        benchmarkExperimentId=request.benchmark_experiment_id,
        items=rows,
    )


def _validate_compare_request(request: CompareExperimentsRequest) -> None:
    if len(request.experiment_ids) < 2:
        raise ValidationAppError(
            "experimentIds must contain at least 2 experiment IDs.",
            details={"field": "experimentIds"},
        )
    if len(set(request.experiment_ids)) != len(request.experiment_ids):
        raise ValidationAppError(
            "experimentIds must not contain duplicate IDs.",
            details={"field": "experimentIds"},
        )
    if (
        request.benchmark_experiment_id is not None
        and request.benchmark_experiment_id not in request.experiment_ids
    ):
        raise ValidationAppError(
            "benchmarkExperimentId must be one of experimentIds.",
            details={"field": "benchmarkExperimentId"},
        )
