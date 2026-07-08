# M27: Multi-Agent Pipeline

## Goal

Integrate the multi-agent paper-trading pipeline while preserving the existing
execution invariant:

```text
Agent output -> TradingDecision -> RiskCheck -> Order/Trade
```

## Scope

- Keep `AgentMode.PIPELINE` as the persisted backend value.
- Present the mode as Multi Agent in the frontend.
- Agents remain advisory and must not access broker, database, scheduler,
  market-data, or secret APIs directly.

## Acceptance Criteria

- Multi Agent paper trading produces auditable agent logs.
- Exactly one final `TradingDecision` is persisted per execution.
- RiskCheck remains mandatory before any paper order.
- Single Agent behavior remains compatible.

