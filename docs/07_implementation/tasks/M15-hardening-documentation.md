# M15: Hardening and Documentation

## Goal

Align README, API docs, frontend route docs, domain rules, architecture notes,
environment examples, and runbooks with the implemented M0-M13 plus frontend
chart-polish behavior.

---

## Scope

- Documentation update.
- API/OpenAPI alignment.
- Frontend route documentation alignment.
- Safety-boundary documentation.
- Environment/config documentation.
- Test/build/runbook cleanup.
- Small warning/config cleanup only if behavior-preserving.

---

## Out of Scope

- No new endpoints.
- No database migration, table, column, or enum changes.
- No new strategy, agent, broker, scheduler, market-data, paper-trading, or frontend feature behavior.
- No real Alpaca or LLM calls.
- No relaxation of PostgreSQL-backed test behavior.

---

## Acceptance Criteria

- README accurately describes implemented behavior and known limitations.
- `docs/04_api/api-spec.md` and `docs/04_api/openapi.yaml` document only implemented public endpoints.
- Frontend docs list implemented routes and mark execution-step/order/trade/agent-log public detail UI as deferred.
- Domain and architecture docs preserve the Strategy/Agent -> TradingDecision -> RiskCheck -> ExecutionStep -> Order/Trade invariant.
- Runbook commands are current for PostgreSQL host port `5433`, backend `uv`, frontend `npm`, and Docker Compose.
- Backend lint, backend PostgreSQL suite, frontend build, and Docker Compose config pass.
