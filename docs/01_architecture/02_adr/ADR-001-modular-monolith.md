# ADR-001: Modular Monolith

## Status

Accepted

## Context

Trading Lab is a web-based strategy and agentic-AI trading experimentation platform for SPY simulation and paper trading.

The system includes several distinct concerns:

- experiment lifecycle management
- strategy execution
- agentic-AI decision generation
- risk validation
- execution orchestration
- market data access
- paper-trading broker integration
- portfolio and metrics calculation
- persistence and audit logging
- frontend dashboard and comparison views

A possible architecture would be to split these concerns into multiple microservices. However, Version 1 is intended for a single-user, local Docker Compose deployment and should remain simple enough to develop, debug, and operate.

## Decision

Trading Lab will be implemented as a modular monolith in Version 1.

The backend is deployed as one FastAPI application, but internally separated into clear modules:

- API Routes
- Experiment Module
- Scheduler Module
- Execution Module
- Strategy Module
- Agent Module
- Risk Module
- Market Data Module
- Broker Module
- Metrics Module
- Persistence Layer
- Domain Model

## Rationale

A modular monolith provides enough internal structure without the operational complexity of microservices.

It allows the system to enforce clear module boundaries while keeping:

- deployment simple
- debugging straightforward
- database transactions easier
- local development faster
- Docker Compose setup minimal
- architecture easier to understand for developers and AI coding agents

The system can later evolve toward separated services if scaling, deployment, or team boundaries require it.

## Alternatives Considered

### Microservices

Rejected for Version 1.

Microservices would introduce additional complexity:

- service discovery
- network communication
- distributed tracing
- message queues
- separate deployments
- harder local development
- more difficult transaction boundaries

This is unnecessary for a single-user Version 1 system.

### Single unstructured backend

Rejected.

A single backend without clear module boundaries would be easier initially, but would create architecture drift quickly. The system requires strict separation between strategies, agents, risk checks, execution, broker access, and persistence.

## Consequences

### Positive

- simpler deployment
- simpler local development
- easier debugging
- clear internal modularity
- easier transaction handling
- lower infrastructure overhead
- good fit for Docker Compose

### Negative

- all backend modules are deployed together
- scaling individual modules independently is not possible in V1
- module boundaries must be enforced by code structure and review discipline rather than network boundaries

## Implementation Rules

- Backend modules must remain separated by responsibility.
- API routes must not contain business logic.
- Strategies and agents must not call Broker or Market Data integrations directly.
- Broker access must remain inside the Broker Module.
- Market data access must remain inside the Market Data Module.
- LLM access must remain inside the Agent Module or LLM client abstraction.
- Persistence access should go through repositories or explicit persistence services.
- Cross-module calls should follow the documented execution pipeline.

## Related Documents

- `../system-overview.md`
- `../01_c4-model/c4-container.md`
- `../01_c4-model/c4-component.md`
- `../decisions.md`
