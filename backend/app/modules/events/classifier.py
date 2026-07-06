from decimal import Decimal

from app.domain.enums import ImpactDirection, NewsEventSeverity, NewsEventType
from app.modules.events.types import ClassifiedEvent, NewsArticle


class DeterministicEventClassifier:
    def classify(self, article: NewsArticle, symbol: str) -> ClassifiedEvent:
        text = f"{article.headline} {article.summary or ''}".lower()
        if any(token in text for token in ("downgrade", "lawsuit", "probe")):
            return self._result(
                NewsEventType.ANALYST_DOWNGRADE,
                NewsEventSeverity.HIGH,
                ImpactDirection.NEGATIVE,
                "Negative analyst/regulatory language matched.",
            )
        if any(token in text for token in ("upgrade", "beat", "record profit")):
            return self._result(
                NewsEventType.ANALYST_UPGRADE,
                NewsEventSeverity.MEDIUM,
                ImpactDirection.POSITIVE,
                "Positive analyst/earnings language matched.",
            )
        if any(token in text for token in ("fed", "rate", "inflation", "cpi")):
            return self._result(
                NewsEventType.FED_RATE_DECISION,
                NewsEventSeverity.MEDIUM,
                ImpactDirection.NEUTRAL,
                "Macro monetary-policy language matched.",
            )
        if any(token in text for token in ("war", "conflict", "sanction")):
            return self._result(
                NewsEventType.GEOPOLITICAL_RISK,
                NewsEventSeverity.HIGH,
                ImpactDirection.NEGATIVE,
                "Geopolitical risk language matched.",
            )
        relevance = Decimal("0.7000") if symbol.upper() in article.symbols else Decimal("0.3000")
        return ClassifiedEvent(
            event_type=NewsEventType.GENERAL_MARKET_NEWS,
            severity=NewsEventSeverity.LOW,
            impact_direction=ImpactDirection.NEUTRAL,
            relevance_score=relevance,
            rationale="General market news classified deterministically.",
        )

    def _result(
        self,
        event_type: NewsEventType,
        severity: NewsEventSeverity,
        impact_direction: ImpactDirection,
        rationale: str,
    ) -> ClassifiedEvent:
        return ClassifiedEvent(
            event_type=event_type,
            severity=severity,
            impact_direction=impact_direction,
            relevance_score=Decimal("0.8500"),
            rationale=rationale,
        )
