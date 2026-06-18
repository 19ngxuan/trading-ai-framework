# M25: Hardening and Documentation Update

## Goal

Align documentation, API contracts, safety boundaries, environment examples,
and runbooks with the implemented M0-M24 system before further feature work.

## Scope

- README update.
- API specification and OpenAPI alignment.
- Domain workflow and business-rule alignment.
- Architecture decision and system-overview alignment.
- Frontend route documentation alignment where needed.
- Roadmap/task index cleanup.
- Small behavior-preserving documentation and contract fixes only.

## Out of Scope

- No new endpoints.
- No database migrations, tables, columns, or enum values.
- No trading, broker, scheduler, market-data, agent, or frontend feature changes.
- No real Alpaca or LLM calls in tests.
- No relaxation of PostgreSQL-backed test behavior.

## Acceptance Criteria

- README accurately describes implemented M0-M24 behavior and limitations.
- `docs/04_api/api-spec.md` and `docs/04_api/openapi.yaml` describe only
  implemented public endpoints and fields.
- Architecture and domain docs preserve the Strategy/Agent -> TradingDecision ->
  RiskCheck -> ExecutionStep -> Order/Trade invariant.
- ScaDS.AI paper-agent scope is documented as paper single-agent only.
- Runbook commands remain current for Docker, PostgreSQL host port `5433`,
  backend `uv`, and frontend `npm`.

