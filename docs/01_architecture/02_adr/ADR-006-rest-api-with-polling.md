# ADR-006: REST API with Polling

## Status

Accepted

## Context

The React frontend needs to interact with the FastAPI backend for:

- experiment creation
- experiment status changes
- dashboard data
- experiment detail data
- metrics
- trades
- orders
- execution steps
- agent logs
- events
- comparison views

Dashboard data should update automatically, but Version 1 does not require true real-time streaming. The system is designed for daily, weekly, or monthly trading frequencies, not high-frequency trading.

## Decision

Frontend-backend communication uses REST APIs in Version 1.

Dashboard updates use polling.

WebSockets and Server-Sent Events are not part of V1.

## Rationale

REST with polling is sufficient for the expected system behavior and is simpler to implement.

Benefits:

- easy to reason about
- easy to test
- works well with TanStack Query
- avoids WebSocket lifecycle complexity
- sufficient for low-frequency experiment updates

## Alternatives Considered

### WebSockets

Rejected for V1.

WebSockets add complexity that is not justified by the expected update frequency.

### Server-Sent Events

Rejected for V1.

SSE may be useful later, but REST polling is simpler and adequate.

### GraphQL

Rejected for V1.

REST maps well to the resource-oriented API design and FastAPI.

## Consequences

### Positive

- simple frontend-backend communication
- easier testing
- compatible with API documentation
- simple polling with TanStack Query
- fewer infrastructure concerns

### Negative

- polling may fetch unchanged data
- not ideal for high-frequency real-time updates
- future real-time UX may require SSE or WebSockets

## Implementation Rules

- All API endpoints must be under `/api/v1`.
- Start and run-next-step actions should return `202 Accepted` when asynchronous.
- Dashboard should use polling intervals, such as 5-15 seconds.
- Long-running jobs must not block frontend requests.
- API responses should use consistent schemas.
- Error responses should use standardized error format.

## Related Documents

- `../system-overview.md`
- `../c4-container.md`
- `../decisions.md`
- `../../03_api/api-spec.md`
