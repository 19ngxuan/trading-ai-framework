from collections.abc import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import Settings
from app.modules.scheduler.jobs import (
    BrokerSyncRunResult,
    PaperSchedulerTickResult,
    SchedulerTickResult,
    sync_open_paper_broker_orders,
    trigger_due_experiments,
    trigger_due_paper_trading_experiments,
)


def create_scheduler(
    settings: Settings,
    job_func: Callable[[], SchedulerTickResult] = trigger_due_experiments,
    paper_job_func: Callable[[], PaperSchedulerTickResult] | None = None,
    broker_sync_job_func: Callable[[], BrokerSyncRunResult] = sync_open_paper_broker_orders,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    if settings.scheduler_enabled:
        scheduler.add_job(
            job_func,
            trigger="interval",
            seconds=settings.scheduler_interval_seconds,
            id=settings.scheduler_job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    if settings.paper_trading_scheduler_enabled:
        scheduler.add_job(
            paper_job_func
            or (
                lambda: trigger_due_paper_trading_experiments(
                    daily_evaluation_time=settings.paper_trading_daily_evaluation_time,
                    paper_trading_test_mode_enabled=(
                        settings.paper_trading_test_mode_enabled
                    ),
                )
            ),
            trigger="interval",
            seconds=settings.paper_trading_scheduler_interval_seconds,
            id=settings.paper_trading_scheduler_job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            broker_sync_job_func,
            trigger="interval",
            seconds=settings.paper_trading_scheduler_interval_seconds,
            id=f"{settings.paper_trading_scheduler_job_id}_broker_sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    return scheduler
