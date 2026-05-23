from collections.abc import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import Settings
from app.modules.scheduler.jobs import SchedulerTickResult, trigger_due_experiments


def create_scheduler(
    settings: Settings,
    job_func: Callable[[], SchedulerTickResult] = trigger_due_experiments,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        job_func,
        trigger="interval",
        seconds=settings.scheduler_interval_seconds,
        id=settings.scheduler_job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
