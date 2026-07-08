# M29: Autonomous Multi-Agent Paper Trading

## Goal

Make Multi Agent paper trading run through the existing paper scheduler, rather
than requiring manual execution for normal operation.

## Scope

- Support scheduled paper execution for configured `AGENTIC_AI` + `PIPELINE`
  experiments.
- Preserve lifecycle behavior: start is lifecycle-only, pause/stop prevent new
  strategy steps, broker sync continues for open submitted orders.
- Keep agent output advisory and RiskCheck-authoritative.

## Acceptance Criteria

- Scheduler can pick up eligible running Multi Agent paper experiments.
- Duplicate due slots do not create duplicate execution steps or orders.
- HOLD or rejected RiskCheck never submits a broker order.
- No real-money trading path is introduced.

