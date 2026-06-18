# M21: Paper Trading Operations UI

## Goal

Expose read-only operational visibility for paper trading so users can
understand scheduler state, persisted orders, trades, broker sync logs, and
paper-trading status.

## Implemented Scope

- Read-only experiment-scoped endpoints:
  - `GET /api/v1/experiments/{experiment_id}/orders`
  - `GET /api/v1/experiments/{experiment_id}/trades`
  - `GET /api/v1/experiments/{experiment_id}/broker-sync-logs`
  - `GET /api/v1/experiments/{experiment_id}/paper-status`
- Frontend paper status card and read-only operations tabs.
- Paper status explains scheduler/configuration state and strategy-specific
  operational metadata.

## Boundaries

- No broker polling from read endpoints.
- No order submission, retry, cancellation, or manual sync action.
- No account or position reconciliation.
- No schema migration.

