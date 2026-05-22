# UI Routes

## 1. Purpose

This document defines the frontend routing structure for Trading Lab.

It describes the main application routes, their responsibilities, expected data dependencies, user actions, and related backend API endpoints.

The frontend is implemented with React and TypeScript. Routing is handled with React Router. Data loading, caching, mutations, and polling are handled with TanStack Query.

This document is not a visual design specification. Component details are documented in `components.md`.

---

## 2. Routing Principles

The frontend routes must follow these principles:

1. The frontend communicates only with the Backend API.
2. The frontend must not call Alpaca, the LLM provider, or the database directly.
3. The frontend must not contain trading logic, risk logic, broker logic, or agent decision logic.
4. The frontend displays backend state and sends user commands to backend endpoints.
5. The backend remains the source of truth for experiment state, portfolio state, metrics, trades, orders, logs, and agent decisions.
6. Dashboard and detail pages use polling for updates in Version 1.
7. Route-level pages should remain thin and delegate UI sections to feature components.

Historical simulation progress is tracked by polling. V1 does not use WebSockets, SSE, external queues, or worker-specific endpoints.

---

## 3. Route Overview

The Version 1 frontend contains these routes:

```text
/
 /dashboard
 /experiments
 /experiments/new
 /experiments/:experimentId
 /execution-steps/:executionStepId
 /compare
 /events
 /settings
```

Recommended redirect:

```text
/ -> /dashboard
```

---

## 4. Application Layout

All main routes use the same application shell:

```text
AppLayout
├── Sidebar
├── Header
└── Page Content
```

Sidebar entries:

- Dashboard
- Experiments
- Compare
- Events
- Settings

The sidebar is the primary navigation mechanism.

---

## 5. `/dashboard`

## 5.1 Purpose

The Dashboard is the main overview page.

It answers:

- Which experiments exist?
- Which experiments are currently running?
- Which experiments have errors?
- Which strategies perform best?
- How do experiments compare against Buy and Hold?

## 5.2 Main UI Sections

- KPI cards
- Experiment table
- Recent error summary
- Optional latest agent-decision summary

## 5.3 Data Dependencies

Backend endpoints:

```http
GET /api/v1/experiments
```

Optional:

```http
GET /api/v1/experiments/{id}/events
```

## 5.4 Polling

The dashboard should poll experiment summaries every 5-15 seconds.

## 5.5 User Actions

From the dashboard the user can:

- open experiment detail
- create a new experiment
- start an experiment
- pause an experiment
- resume an experiment
- stop an experiment
- run next step
- navigate to comparison view

## 5.6 Route Rules

The dashboard may show action buttons, but it must not decide whether a transition is valid based only on frontend logic.

The backend validates status transitions.

Show Start for `CREATED`, Resume for `PAUSED`, Pause/Stop for `RUNNING`. Backend remains authoritative and rejects invalid transitions.

---

## 6. `/experiments`

## 6.1 Purpose

The Experiments page provides a list-oriented view of all experiments.

It is similar to the dashboard table but may provide more filtering and sorting.

## 6.2 Main UI Sections

- Experiment table
- Status filters
- Strategy filters
- Mode filters
- Search by experiment name
- Create Experiment button

## 6.3 Data Dependencies

```http
GET /api/v1/experiments?status=...&strategyType=...&mode=...&limit=...&offset=...
```

## 6.4 User Actions

- open experiment detail
- create experiment
- start / pause / resume / stop
- run next step
- add experiment to compare selection

---

## 7. `/experiments/new`

## 7.1 Purpose

The Create Experiment page allows the user to configure a new experiment.

After creation, the experiment remains in `CREATED` status and must be started manually.

## 7.2 Main UI Sections

- Basic Configuration
- Strategy Configuration
- Risk Configuration
- Fee Configuration
- Submit / Cancel actions

## 7.3 Form Fields

Basic Configuration:

- experiment name
- mode
- strategy type
- asset symbol
- initial capital
- start date
- end date
- trading frequency
- fee model type
- fee value

Strategy Configuration:

For `BUY_AND_HOLD`:

- strategy version
- optional parameters

For `MOVING_AVERAGE`:

- moving average window
- position sizing type
- strategy version
- optional parameters

For `AGENTIC_AI`:

- agent mode
- model name
- confidence threshold
- strategy version
- optional parameters such as `useRsi`, `useNewsSentiment`, or `allowPositionSizeSuggestion`

Risk Configuration:

- `maxPositionSizePct`: number, required by effective defaults, `0 < value <= 1`, default `1.0`
- `maxTradesPerDay`: integer or null, if set `>= 1`, default `null`
- `maxTradesPerWeek`: integer or null, if set `>= 1`, default `null`
- `maxDrawdownPct`: number or null, if set `0 < value <= 1`, default `null`
- `drawdownAction`: `BLOCK_TRADES`, `PAUSE_EXPERIMENT`, or `STOP_EXPERIMENT`, default `BLOCK_TRADES`
- `fallbackAction`: V1 must be `HOLD`, default `HOLD`

Risk configuration is represented through `strategyConfig.parametersJson.riskConfig` in V1.

## 7.4 Data Dependencies

```http
GET /api/v1/options
POST /api/v1/experiments
```

## 7.5 Success Behavior

After successful creation:

Preferred behavior:

```text
Navigate to /experiments/:experimentId
```

Alternative behavior:

```text
Navigate to /dashboard
```

## 7.6 Route Rules

The form must not hardcode option values if they can be loaded through `/api/v1/options`.

The frontend validates basic required fields for usability, but backend validation remains authoritative.

---

## 8. `/experiments/:experimentId`

## 8.1 Purpose

The Experiment Detail page is the main analysis page for a single experiment.

It shows configuration, status, metrics, charts, trades, orders, execution steps, agent logs, events, and config details.

## 8.2 Main UI Layout

```text
ExperimentDetailPage
├── Header
├── Action Bar
├── KPI Row
├── Performance Chart
└── Tabs
    ├── Overview
    ├── Trades
    ├── Orders
    ├── Execution Steps
    ├── Metrics
    ├── Agent Logs
    ├── Events
    └── Config
```

## 8.3 Data Dependencies

```http
GET /api/v1/experiments/{experimentId}
GET /api/v1/experiments/{experimentId}/portfolio-snapshots
GET /api/v1/experiments/{experimentId}/metrics
GET /api/v1/experiments/{experimentId}/trades
GET /api/v1/experiments/{experimentId}/orders
GET /api/v1/experiments/{experimentId}/execution-steps
GET /api/v1/experiments/{experimentId}/agent-logs
GET /api/v1/experiments/{experimentId}/events
```

## 8.4 Polling

The detail page should poll the main experiment detail endpoint while the experiment is in:

- `RUNNING`
- `PAUSED` if sync errors or events may update
- `FAILED` for a short time after transition

Polling can be disabled or reduced for:

- `COMPLETED`
- `STOPPED`

## 8.5 User Actions

- start
- pause
- resume
- stop
- run next step
- open compare view with this experiment preselected
- open execution step detail
- expand agent decision logs
- filter events

## 8.6 Tab Rules

The `Agent Logs` tab should be visible for all experiments but may display an empty state for non-agentic strategies.

The `Events` tab must show errors and warnings clearly.

The `Config` tab must show immutable configuration used by the experiment.

---

## 9. `/execution-steps/:executionStepId`

## 9.1 Purpose

The Execution Step Detail page is the technical audit screen for one execution step.

It answers:

```text
What exactly happened in this execution step?
```

## 9.2 Main UI Sections

- ExecutionStep summary
- MarketDataSnapshot
- TradingDecision
- RiskCheck
- Order
- Trades
- PortfolioSnapshot
- MetricSnapshot
- AgentDecisionLogs
- SystemEventLogs

## 9.3 Data Dependencies

```http
GET /api/v1/execution-steps/{executionStepId}
```

## 9.4 User Actions

- navigate back to experiment detail
- open related agent log details
- inspect JSON payloads
- inspect errors
- copy diagnostic payloads

## 9.5 Route Rules

This page is primarily a debugging and audit view.

It may display technical JSON structures.

It must not provide direct order execution or broker actions.

The order section must handle `order = null` for HOLD or blocked decisions. The trades section renders an array and may be empty because one order may produce zero, one, or many fills.

---

## 10. `/compare`

## 10.1 Purpose

The Compare page is a central user-facing screen because strategy and agent comparison is a core product goal.

It allows users to compare multiple experiments against a benchmark, usually Buy and Hold.

## 10.2 Main UI Sections

- experiment selector
- benchmark selector
- comparison KPI table
- ranking table
- equity curve chart
- return curve chart
- drawdown comparison

## 10.3 Data Dependencies

```http
GET /api/v1/experiments
POST /api/v1/experiments/compare
```

Optional for charts:

```http
GET /api/v1/experiments/{experimentId}/portfolio-snapshots
GET /api/v1/experiments/{experimentId}/metrics
```

## 10.4 User Actions

- select experiments
- select benchmark
- compare experiments
- toggle chart mode: Portfolio Value / Return
- open experiment detail from comparison result

## 10.5 Route Rules

The page should show clearly if experiments have incompatible time windows or incomplete metrics.

The backend should remain authoritative for comparison calculations.

---

## 11. `/events`

## 11.1 Purpose

The Events page provides a system-wide view of warnings and errors.

It helps diagnose:

- market data issues
- broker errors
- broker-state mismatches
- invalid LLM output
- repair attempts
- fallback HOLD usage
- risk limit triggers
- failed execution steps

## 11.2 Main UI Sections

- event filters
- event table
- event detail panel

## 11.3 Data Dependencies

Version 1 may use one of the following:

```http
GET /api/v1/events
```

or experiment-scoped endpoints:

```http
GET /api/v1/experiments/{experimentId}/events
```

If a global events endpoint is not implemented initially, the Events page may be deferred or backed by experiment-scoped event queries.

## 11.4 Filters

- experiment
- level
- event type
- date range

## 11.5 Route Rules

Events should be displayed in reverse chronological order.

ERROR events must be visually distinguishable.

---

## 12. `/settings`

## 12.1 Purpose

The Settings page shows local development and integration status.

It does not expose secrets.

## 12.2 Main UI Sections

- environment status
- backend health
- database health
- scheduler status
- Alpaca Market Data configured
- Alpaca Paper Trading configured
- LLM Provider configured
- paper-trading-only status

## 12.3 Data Dependencies

Recommended endpoint:

```http
GET /api/v1/options
GET /api/v1/health
```

Optional future endpoint:

```http
GET /api/v1/settings/status
```

## 12.4 Route Rules

The Settings page must not display API keys or secret values.

It may show only boolean configuration states such as `configured: true`.

---

## 13. Error Handling

Frontend error handling should use the backend error format:

```json
{
  "errorCode": "INVALID_EXPERIMENT_STATUS",
  "message": "Experiment cannot be started because it is already running.",
  "details": {
    "experimentId": 1,
    "currentStatus": "RUNNING"
  }
}
```

Frontend behavior:

- show user-readable message
- preserve technical details in expandable section if useful
- do not swallow errors silently
- do not retry mutating actions automatically unless explicitly designed

---

## 14. Loading and Empty States

Each route should define loading and empty states.

Examples:

Dashboard:

```text
No experiments yet. Create your first experiment.
```

Agent Logs tab:

```text
No agent logs for this experiment.
```

Events tab:

```text
No events found for selected filters.
```

Compare page:

```text
Select at least two experiments to compare.
```

---

## 15. Related Documents

- `../01_architecture/system-overview.md`
- `../01_architecture/01_c4-model/c4-container.md`
- `../01_architecture/01_c4-model/c4-component.md`
- `../02_domain/01_entities.md`
- `../02_domain/02_workflows.md`
- `../04_api/api-spec.md`
- `./components.md`
