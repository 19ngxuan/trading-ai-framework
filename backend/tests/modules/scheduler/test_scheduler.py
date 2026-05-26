import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.scheduler.scheduler import create_scheduler


def test_invalid_enabled_scheduler_interval_fails_config_validation() -> None:
    with pytest.raises(ValidationError):
        Settings(scheduler_enabled=True, scheduler_interval_seconds=0)


def test_invalid_enabled_paper_scheduler_config_fails_validation() -> None:
    with pytest.raises(ValidationError):
        Settings(
            paper_trading_scheduler_enabled=True,
            alpaca_paper_trading_enabled=True,
            paper_trading_scheduler_interval_seconds=0,
        )
    with pytest.raises(ValidationError):
        Settings(
            paper_trading_scheduler_enabled=True,
            alpaca_paper_trading_enabled=True,
            paper_trading_daily_evaluation_time="bad",
        )
    with pytest.raises(ValidationError):
        Settings(paper_trading_scheduler_enabled=True)


def test_create_scheduler_registers_interval_job() -> None:
    settings = Settings(
        scheduler_enabled=True,
        scheduler_interval_seconds=7,
        scheduler_job_id="test_scheduler_job",
    )

    scheduler = create_scheduler(settings)

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "test_scheduler_job"
    assert str(jobs[0].trigger) == "interval[0:00:07]"


def test_create_scheduler_registers_paper_jobs() -> None:
    settings = Settings(
        paper_trading_scheduler_enabled=True,
        paper_trading_scheduler_interval_seconds=11,
        paper_trading_scheduler_job_id="paper_job",
        alpaca_paper_trading_enabled=True,
        alpaca_api_key_id="key",
        alpaca_api_secret_key="secret",
    )

    scheduler = create_scheduler(settings)

    jobs = sorted(scheduler.get_jobs(), key=lambda item: item.id)
    assert [job.id for job in jobs] == ["paper_job", "paper_job_broker_sync"]
    assert {str(job.trigger) for job in jobs} == {"interval[0:00:11]"}


def test_disabled_config_does_not_start_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    get_settings.cache_clear()

    def fail_if_called(settings):
        raise AssertionError("Scheduler should not be created when disabled.")

    monkeypatch.setattr("app.main.create_scheduler", fail_if_called)

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert not hasattr(client.app.state, "scheduler")

    get_settings.cache_clear()


def test_enabled_config_starts_and_shuts_down_scheduler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeScheduler:
        def __init__(self) -> None:
            self.started = False
            self.shutdown_called = False
            self.shutdown_wait: bool | None = None

        def start(self) -> None:
            self.started = True

        def shutdown(self, wait: bool = True) -> None:
            self.shutdown_called = True
            self.shutdown_wait = wait

    fake_scheduler = FakeScheduler()

    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "5")
    get_settings.cache_clear()
    monkeypatch.setattr("app.main.create_scheduler", lambda settings: fake_scheduler)

    with TestClient(create_app()) as client:
        assert fake_scheduler.started is True
        assert client.app.state.scheduler is fake_scheduler

    assert fake_scheduler.shutdown_called is True
    assert fake_scheduler.shutdown_wait is False
    get_settings.cache_clear()
