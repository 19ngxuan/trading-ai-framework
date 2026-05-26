# Frontend Components

## 1. Purpose

This document defines the main frontend component structure for Trading Lab.

It describes reusable layout components, feature components, data-display components, and component-level rules.

The frontend is implemented with:

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Recharts
- TanStack Query
- React Router

This document should guide implementation and prevent frontend components from taking over backend responsibilities.

---

## 2. Component Principles

Frontend components must follow these principles:

1. Components display state returned by the Backend API.
2. Components may trigger backend commands through API mutations.
3. Components must not contain trading logic.
4. Components must not contain risk validation logic.
5. Components must not call Alpaca, the LLM provider, or the database.
6. Components should be typed with TypeScript.
7. API calls should be centralized in the `api/` layer.
8. Server state should be managed with TanStack Query.
9. UI state should remain local unless shared state is required.
10. Large feature areas should be grouped under `features/`.

---

## 3. Recommended Frontend Structure

```text
frontend/src/
├── main.tsx
├── app/
│   ├── App.tsx
│   ├── queryClient.ts
│   └── layout/
│       ├── AppLayout.tsx
│       ├── Sidebar.tsx
│       └── Header.tsx
│
├── api/
│   ├── client.ts
│   ├── experimentsApi.ts
│   ├── executionStepsApi.ts
│   ├── metricsApi.ts
│   ├── tradesApi.ts
│   ├── ordersApi.ts
│   ├── agentLogsApi.ts
│   ├── eventsApi.ts
│   ├── comparisonApi.ts
│   └── optionsApi.ts
│
├── routes/
│   └── router.tsx
│
├── pages/
│   ├── DashboardPage.tsx
│   ├── ExperimentsPage.tsx
│   ├── CreateExperimentPage.tsx
│   ├── ExperimentDetailPage.tsx
│   ├── ExecutionStepDetailPage.tsx
│   ├── ComparePage.tsx
│   ├── EventsPage.tsx
│   └── SettingsPage.tsx
│
├── features/
│   ├── dashboard/
│   ├── experiments/
│   ├── experimentDetail/
│   ├── comparison/
│   ├── agentLogs/
│   ├── events/
│   └── settings/
│
├── components/
│   ├── ui/
│   ├── charts/
│   ├── tables/
│   ├── status/
│   └── json/
│
├── types/
│   ├── experiment.ts
│   ├── executionStep.ts
│   ├── metrics.ts
│   ├── trade.ts
│   ├── order.ts
│   ├── agentLog.ts
│   ├── event.ts
│   └── api.ts
│
└── utils/
```

---

## 4. App-Level Components

## 4.1 `App`

Responsibility:

- root application component
- registers global providers
- renders router

Must include:

- TanStack Query provider
- Router provider
- global error boundary if implemented

## 4.2 `AppLayout`

Responsibility:

- provides main shell for authenticated/local app routes
- renders sidebar
- renders header
- renders page content outlet

The layout should be reused across all main routes.

## 4.3 `Sidebar`

Responsibility:

- navigation between main routes

Entries:

- Dashboard
- Experiments
- Compare
- Events
- Settings

## 4.4 `Header`

Responsibility:

- displays current page title
- optional environment indicator
- optional backend health indicator

Must not display secrets.

---

## 5. API Layer Components

The `api/` folder provides frontend wrappers for backend endpoints.

## 5.1 `client.ts`

Responsibility:

- configure API base URL
- wrap fetch or HTTP client
- parse JSON
- normalize backend errors
- expose typed request helpers

The API client must understand the backend error shape:

```json
{
  "errorCode": "VALIDATION_ERROR",
  "message": "Human-readable message",
  "details": {}
}
```

## 5.2 API Files

Recommended files:

- `experimentsApi.ts`
- `executionStepsApi.ts`
- `metricsApi.ts`
- `tradesApi.ts`
- `ordersApi.ts`
- `agentLogsApi.ts`
- `eventsApi.ts`
- `comparisonApi.ts`
- `optionsApi.ts`

Each file should export typed functions.

Example conceptual functions:

```text
listExperiments(params)
getExperiment(id)
createExperiment(payload)
startExperiment(id)
pauseExperiment(id)
resumeExperiment(id)
stopExperiment(id)
runNextStep(id)
getExecutionStep(id)
getTrades(experimentId, params)
getMetrics(experimentId, params)
getAgentLogs(experimentId, params)
compareExperiments(payload)
getOptions()
```

---

## 6. Dashboard Components

Recommended location:

```text
features/dashboard/
```

Components:

```text
DashboardKpiCards
ExperimentSummaryTable
RecentErrorsPanel
LatestAgentDecisionBadge
```

## 6.1 `DashboardKpiCards`

Displays aggregate information:

- running experiments
- completed experiments
- failed experiments
- best performer
- open errors

The component must not compute trading metrics from raw trade data. It should display already provided summary values.

## 6.2 `ExperimentSummaryTable`

Displays compact experiment summaries.

Columns:

- Name
- Strategy
- Mode
- Status
- Asset
- Portfolio Value
- Return
- P/L
- Max Drawdown
- Trades
- vs Buy and Hold
- Last Decision
- Last Error
- Actions

## 6.3 `ExperimentActions`

Reusable component for experiment commands:

- Start
- Pause
- Resume
- Stop
- Run Next Step
- Open
- Compare

Start is for `CREATED`; Resume is for `PAUSED`; Start must not be shown for `PAUSED`.

Action visibility may be based on current status for UX, but backend remains authoritative.

Invalid transitions must be handled gracefully if the backend rejects them.

---

## 7. Experiment Creation Components

Recommended location:

```text
features/experiments/
```

Components:

```text
CreateExperimentForm
BasicExperimentSection
StrategyConfigSection
RiskConfigSection
FeeConfigSection
```

## 7.1 `CreateExperimentForm`

Responsibility:

- collect experiment configuration
- perform basic client-side validation
- submit payload to `POST /api/v1/experiments`

Must load selectable values from:

```http
GET /api/v1/options
```

Must not hardcode enum values if backend options are available.

## 7.2 `BasicExperimentSection`

Fields:

- name
- mode
- strategy type
- asset symbol
- initial capital
- start date
- end date
- trading frequency

## 7.3 `StrategyConfigSection`

Fields depend on selected strategy type.

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
- prompt or strategy version
- optional parameters

## 7.4 `RiskConfigSection`

Risk configuration may include:

- `maxPositionSizePct`: number, required by effective defaults, `0 < value <= 1`, default `1.0`
- `maxTradesPerDay`: integer or null, if set `>= 1`, default `null`
- `maxTradesPerWeek`: integer or null, if set `>= 1`, default `null`
- `maxDrawdownPct`: number or null, if set `0 < value <= 1`, default `null`
- `drawdownAction`: `BLOCK_TRADES`, `PAUSE_EXPERIMENT`, or `STOP_EXPERIMENT`, default `BLOCK_TRADES`
- `fallbackAction`: V1 must be `HOLD`, default `HOLD`

In V1, these fields are stored in `strategyConfig.parametersJson.riskConfig`.

## 7.5 `FeeConfigSection`

Fields:

- fee model type
- fee value

---

## 8. Experiment Detail Components

Recommended location:

```text
features/experimentDetail/
```

Components:

```text
ExperimentHeader
ExperimentActionBar
ExperimentKpiRow
PerformanceChartPanel
ExperimentTabs
OverviewTab
TradesTab
OrdersTab
ExecutionStepsTab
MetricsTab
AgentLogsTab
EventsTab
ConfigTab
```

## 8.1 `ExperimentHeader`

Displays:

- experiment name
- strategy type
- mode
- status
- asset
- start date
- end date
- initial capital

## 8.2 `ExperimentActionBar`

Provides:

- start
- pause
- resume
- stop
- run next step
- compare

Uses the same mutation hooks as dashboard actions.

## 8.3 `ExperimentKpiRow`

Displays:

- current portfolio value
- total return
- profit/loss
- max drawdown
- number of trades
- difference to Buy and Hold

## 8.4 `PerformanceChartPanel`

Displays chart controls:

- Portfolio Value over time
- Return over time
- show/hide Buy-and-Hold benchmark

Uses chart components from `components/charts/`.

## 8.5 `ExperimentTabs`

Tabs:

- Overview
- Trades
- Orders
- Execution Steps
- Metrics
- Agent Logs
- Events
- Config

---

## 9. Execution Step Components

Recommended location:

```text
features/experimentDetail/` or `features/executionSteps/
```

Components:

```text
ExecutionStepsTable
ExecutionStepDetail
MarketDataSnapshotPanel
TradingDecisionPanel
RiskCheckPanel
OrderPanel
TradesPanel
PortfolioSnapshotPanel
MetricSnapshotPanel
ExecutionEventsPanel
```

## 9.1 `ExecutionStepsTable`

Columns:

- sequence number
- scheduled for
- trigger type
- status
- action
- risk result
- order status
- portfolio value
- error

Each row links to:

```text
/execution-steps/:executionStepId
```

## 9.2 `ExecutionStepDetail`

Displays the full audit chain for a single step.

It should make this trace visible:

```text
MarketDataSnapshot
→ TradingDecision
→ RiskCheck
→ Order
→ Trade
→ PortfolioSnapshot
→ MetricSnapshot
→ Events
```

---

## 10. Agent Log Components

Recommended location:

```text
features/agentLogs/
```

Components:

```text
AgentLogTable
AgentLogAccordion
AgentDecisionSummary
AgentInputJsonViewer
PromptViewer
RawOutputViewer
ParsedOutputViewer
RepairAttemptPanel
```

## 10.1 `AgentDecisionSummary`

Displays:

- timestamp
- agent mode
- agent step name
- action if available
- confidence if available
- reason if available
- parsing status
- final action after risk check if available

## 10.2 `AgentLogAccordion`

Displays concise summary first, then expandable technical details.

Details may include:

- input JSON
- prompt text
- raw output text
- parsed output JSON
- repair prompt
- repair raw output
- related trading decision
- related risk check

## 10.3 JSON Display

JSON payloads should be shown using a reusable JSON viewer component.

The UI may expose copy-to-clipboard for debugging.

---

## 11. Compare Components

Recommended location:

```text
features/comparison/
```

Components:

```text
ExperimentSelector
BenchmarkSelector
ComparisonKpiTable
ComparisonRankingTable
ComparisonChart
DrawdownComparisonPanel
```

## 11.1 `ExperimentSelector`

Allows selection of multiple experiments.

Should show:

- experiment name
- strategy type
- mode
- status
- date range

## 11.2 `BenchmarkSelector`

Allows selecting the benchmark experiment.

Default benchmark should be a Buy-and-Hold experiment if available.

## 11.3 `ComparisonKpiTable`

Columns:

- experiment
- strategy
- mode
- return
- P/L
- max drawdown
- trades
- benchmark return
- difference to benchmark
- status

## 11.4 `ComparisonChart`

Supports:

- Portfolio Value over time
- Return over time
- multiple experiment lines
- benchmark line

---

## 12. Events Components

Recommended location:

```text
features/events/
```

Components:

```text
EventFilters
EventTable
EventDetailPanel
EventLevelBadge
EventTypeBadge
```

## 12.1 `EventFilters`

Filters:

- experiment
- level
- event type
- date range

## 12.2 `EventTable`

Columns:

- timestamp
- experiment
- level
- event type
- message

## 12.3 `EventDetailPanel`

Displays:

- message
- details JSON
- related execution step
- timestamp

---

## 13. Settings Components

Recommended location:

```text
features/settings/
```

Components:

```text
SettingsStatusPage
IntegrationStatusCard
BackendHealthCard
SchedulerStatusCard
```

## 13.1 `IntegrationStatusCard`

Displays configuration status for:

- Alpaca Market Data
- Alpaca Paper Trading
- LLM Provider
- Database
- Scheduler

Must display only status, never secret values.

---

## 14. Shared Components

Recommended location:

```text
components/
```

## 14.1 `components/charts/`

Components:

```text
InteractiveLineChart
EquityCurveChart
ReturnChart
ComparisonChart
DrawdownChart
SvgLineChart
```

Rules:

- Charts display data passed through props.
- Charts do not fetch data directly.
- Charts do not calculate authoritative metrics.
- Backend-provided metrics remain the source of truth.
- Portfolio, return, and comparison equity charts use the interactive chart
  component for zoom, pan, crosshair, and responsive time-axis behavior.
- `SvgLineChart` remains available for simple lightweight charts that do not
  need interactive trading-style analysis.

## 14.2 `components/status/`

Components:

```text
ExperimentStatusBadge
ExecutionStepStatusBadge
OrderStatusBadge
EventLevelBadge
ParsingStatusBadge
```

## 14.3 `components/json/`

Components:

```text
JsonViewer
JsonPanel
```

Used for:

- agent inputs
- parsed outputs
- raw decision JSON
- event details
- broker sync details

## 14.4 `components/tables/`

Reusable table wrappers may be used for:

- pagination
- loading states
- empty states
- sorting UI

---

## 15. Hooks

Feature hooks should wrap TanStack Query usage.

Recommended hooks:

```text
useExperiments
useExperiment
useCreateExperiment
useExperimentActions
useExecutionSteps
useExecutionStep
useTrades
useOrders
useMetrics
usePortfolioSnapshots
useAgentLogs
useEvents
useCompareExperiments
useOptions
```

Rules:

- Hooks may call API client functions.
- Hooks may define query keys.
- Hooks may configure polling.
- Hooks must not contain trading or risk logic.

---

## 16. TypeScript Types

Types should mirror backend API contracts.

Recommended files:

```text
types/experiment.ts
types/executionStep.ts
types/metrics.ts
types/trade.ts
types/order.ts
types/agentLog.ts
types/event.ts
types/api.ts
```

Important enums:

- `ExperimentMode`
- `StrategyType`
- `ExperimentStatus`
- `TradingFrequency`
- `ExecutionStepStatus`
- `TriggerType`
- `TradeAction`
- `OrderStatus`
- `AgentMode`
- `ParsingStatus`
- `EventLevel`

If OpenAPI type generation is introduced later, generated types should replace or supplement manual types.

---

## 17. UI States

Every data-heavy component must handle:

- loading
- empty
- error
- success

Examples:

Experiment table empty state:

```text
No experiments yet. Create your first experiment.
```

Agent logs empty state:

```text
No agent logs for this experiment.
```

Events empty state:

```text
No events match the selected filters.
```

Compare empty state:

```text
Select at least two experiments to compare.
```

---

## 18. Mutations and Refetching

Mutation actions include:

- create experiment
- start experiment
- pause experiment
- resume experiment
- stop experiment
- run next step
- compare experiments

After successful mutations, related queries should be invalidated.

Examples:

After starting an experiment:

- invalidate experiment detail
- invalidate experiment list
- invalidate events if needed

After running next step:

- invalidate experiment detail
- invalidate execution steps
- invalidate metrics
- invalidate portfolio snapshots
- invalidate trades
- invalidate orders
- invalidate events

---

## 19. Frontend Rules for Agentic AI

Agent-related UI must support auditability.

The UI should show:

- input JSON
- prompt text
- raw output
- parsed output
- parsing status
- repair prompt if used
- repair output if used
- related trading decision
- related risk check

The UI must not allow users to execute raw LLM outputs directly.

Agent output is informational until backend converts it into a `TradingDecision`, validates it, and passes it through risk controls.

---

## 20. Out of Scope for Frontend V1

The following are out of scope for Version 1:

- login/register screens
- user profile
- billing
- mobile-first app
- public landing page
- drag-and-drop no-code strategy builder
- direct Alpaca configuration in frontend
- displaying raw secrets
- live WebSocket streaming
- frontend-side strategy execution
- frontend-side risk validation

---

## 21. Related Documents

- `./ui-routes.md`
- `../01_architecture/01_c4-model/c4-container.md`
- `../01_architecture/01_c4-model/c4-component.md`
- `../02_domain/01_entities.md`
- `../02_domain/02_workflows.md`
- `../04_api/api-spec.md`
- `../05_backend/service-contracts.md`
