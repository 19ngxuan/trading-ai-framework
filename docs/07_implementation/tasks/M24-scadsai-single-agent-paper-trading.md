# M24: ScaDS.AI Single-Agent Paper Trading

## Goal

Enable controlled `AGENTIC_AI` single-agent live paper trading through ScaDS.AI
with frontend model selection, while preserving the execution invariant:

```text
Agent output -> TradingDecision -> RiskCheck -> ExecutionStep -> Order/Trade
```

## Implemented Scope

- `PAPER_TRADING` + `AGENTIC_AI` + `SINGLE_AGENT` + `DAILY` + `SPY`.
- ScaDS.AI OpenAI-compatible provider behind the Agent Module.
- Static allowed-model configuration through:
  - `SCADSAI_LLM_ENABLED`
  - `SCADSAI_API_KEY`
  - `SCADSAI_BASE_URL`
  - `SCADSAI_REQUEST_TIMEOUT_SECONDS`
  - `SCADSAI_ALLOWED_MODELS`
  - `SCADSAI_DEFAULT_MODEL`
- Frontend model selection from `/api/v1/options`.
- Runtime validation checks whether ScaDS.AI is enabled and executable.
- Create validation checks configuration shape and allowed model names.

## Boundaries

- Historical `AGENTIC_AI` remains deterministic fake-provider execution.
- Pipeline-agent paper trading is not implemented.
- ORB/intraday agent paper trading is not implemented.
- No tool calling, prompt editor UI, API-key UI, account reconciliation, outbox,
  or order cancellation.
- Agents must not call broker, Alpaca, persistence, scheduler, environment, or
  secret APIs directly.

