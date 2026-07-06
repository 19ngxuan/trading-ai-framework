from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.domain.enums import EventDecisionStatus
from app.modules.events.alpaca_news_provider import AlpacaNewsProvider
from app.modules.events.classifier import DeterministicEventClassifier
from app.modules.execution.paper_step_runner import PaperTradingStepRunner
from app.persistence.database import create_session_factory
from app.persistence.models import EventAssetImpactModel, EventDecisionModel, NewsEventModel
from app.persistence.repositories import (
    EventAssetImpactRepository,
    EventDecisionRepository,
    ExperimentRepository,
    NewsEventRepository,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EventScannerService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] | None = None,
        settings: Settings | None = None,
        news_provider: AlpacaNewsProvider | None = None,
        classifier: DeterministicEventClassifier | None = None,
        paper_runner: PaperTradingStepRunner | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory or create_session_factory()
        self.news_provider = news_provider or AlpacaNewsProvider(
            api_key_id=self.settings.alpaca_api_key_id or "",
            api_secret_key=self.settings.alpaca_api_secret_key or "",
            base_url=self.settings.alpaca_data_base_url,
            timeout_seconds=self.settings.alpaca_request_timeout_seconds,
        )
        self.classifier = classifier or DeterministicEventClassifier()
        self.paper_runner = paper_runner or PaperTradingStepRunner(
            session_factory=self.session_factory,
            settings=self.settings,
        )

    def scan_once(self) -> dict:
        if not self.settings.event_scanner_enabled:
            return {"enabled": False, "eventsStored": 0, "runsTriggered": 0}
        with self.session_factory() as session:
            experiments = ExperimentRepository(session).list_event_agent_paper_experiments()
            symbols = sorted({experiment.asset_symbol for experiment in experiments})
        if not symbols:
            return {"enabled": True, "eventsStored": 0, "runsTriggered": 0}

        now = _utcnow()
        start = now - timedelta(minutes=self.settings.event_lookback_minutes)
        articles = self.news_provider.fetch_news(
            symbols=symbols,
            start=start,
            end=now,
            limit=self.settings.event_news_limit,
        )

        stored = 0
        triggered = 0
        for article in articles:
            for symbol in symbols:
                if symbol not in article.symbols:
                    continue
                with self.session_factory() as session:
                    event = self._store_event_and_impact(session, article, symbol, now)
                    impact = EventAssetImpactRepository(session).get_by_event_symbol(
                        event.id, symbol
                    )
                    experiment_ids = [
                        experiment.id
                        for experiment in ExperimentRepository(
                            session
                        ).list_event_agent_paper_experiments()
                        if experiment.asset_symbol == symbol
                    ]
                    stored += 1
                    session.commit()
                if impact is None or impact.relevance_score < Decimal(
                    str(self.settings.event_relevance_threshold)
                ):
                    continue
                for experiment_id in experiment_ids:
                    if self._trigger_once(event.id, experiment_id, now):
                        triggered += 1
        return {
            "enabled": True,
            "eventsStored": stored,
            "runsTriggered": triggered,
        }

    def _store_event_and_impact(
        self,
        session: Session,
        article,
        symbol: str,
        now: datetime,
    ) -> NewsEventModel:
        event_repository = NewsEventRepository(session)
        impact_repository = EventAssetImpactRepository(session)
        classified = self.classifier.classify(article, symbol)
        event = event_repository.get_by_provider_external_id(
            article.provider,
            article.external_event_id,
        )
        if event is None:
            event = event_repository.add(
                NewsEventModel(
                    provider=article.provider,
                    external_event_id=article.external_event_id,
                    timestamp=article.timestamp,
                    updated_at=article.updated_at,
                    headline=article.headline,
                    source=article.source,
                    url=article.url,
                    summary=article.summary,
                    event_type=classified.event_type,
                    severity=classified.severity,
                    affected_symbols_json=list(article.symbols),
                    raw_payload_json=article.raw_payload,
                    first_seen_at=now,
                    last_seen_at=now,
                    created_at=now,
                )
            )
            session.flush()
        else:
            event.last_seen_at = now

        impact = impact_repository.get_by_event_symbol(event.id, symbol)
        if impact is None:
            impact_repository.add(
                EventAssetImpactModel(
                    event_id=event.id,
                    symbol=symbol,
                    impact_direction=classified.impact_direction,
                    relevance_score=classified.relevance_score,
                    rationale=classified.rationale,
                    raw_impact_json={
                        "classifier": "deterministic-v1",
                        "articleSymbols": list(article.symbols),
                    },
                    created_at=now,
                )
            )
            session.flush()
        return event

    def _trigger_once(self, event_id: int, experiment_id: int, now: datetime) -> bool:
        with self.session_factory() as session:
            decision_repository = EventDecisionRepository(session)
            existing = decision_repository.get_by_event_experiment(
                event_id,
                experiment_id,
            )
            if existing is not None:
                return False
            decision_repository.add(
                EventDecisionModel(
                    event_id=event_id,
                    experiment_id=experiment_id,
                    execution_step_id=None,
                    trading_decision_id=None,
                    status=EventDecisionStatus.TRIGGERED,
                    reason="Relevant event queued for agent execution.",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()
        try:
            self.paper_runner.run_event_step(
                experiment_id,
                event_id,
                scheduled_for=now,
            )
        except Exception as exc:
            with self.session_factory() as session:
                decision = EventDecisionRepository(session).get_by_event_experiment(
                    event_id,
                    experiment_id,
                )
                if decision is not None:
                    decision.status = EventDecisionStatus.FAILED
                    decision.reason = str(exc)
                    decision.updated_at = _utcnow()
                    session.commit()
            return False
        return True
