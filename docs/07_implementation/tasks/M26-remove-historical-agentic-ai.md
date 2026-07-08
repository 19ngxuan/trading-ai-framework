# M26: Remove Historical Agentic AI Create Support

## Goal

Keep Agentic AI user-facing execution focused on paper trading. Historical
Agentic AI regression code may remain for tests, but the create flow must not
present historical Agentic AI as a supported product path.

## Scope

- Hide or reject user-created `AGENTIC_AI` + `HISTORICAL_SIMULATION` configs.
- Keep rule-based historical strategies unchanged.
- Keep deterministic fake-agent code only where it is still needed for
  regression tests and internal safety checks.

## Acceptance Criteria

- Frontend create UI does not show Agentic AI for historical mode.
- Backend validation rejects unsupported historical Agentic AI create requests.
- Existing historical Buy-and-Hold, Moving Average, and Opening Range Breakout
  behavior remains unchanged.

