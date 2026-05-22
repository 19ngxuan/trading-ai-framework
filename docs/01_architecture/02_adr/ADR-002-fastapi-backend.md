# ADR-002: FastAPI Backend

## Status

Accepted

## Context

Trading Lab requires a backend that can support:

- REST API endpoints for the React frontend
- experiment lifecycle management
- historical simulation workflows
- scheduled execution steps
- broker and market data API integration
- LLM-based agentic-AI workflows
- metrics calculation
- persistence with PostgreSQL
- local Docker Compose deployment

The backend must be suitable for fast iteration and strong integration with Python-based data, trading, and AI tooling.

## Decision

The backend will be implemented with FastAPI and Python.

FastAPI will be used as the main web framework for the Backend API container.

## Rationale

FastAPI is a good fit because Trading Lab is strongly Python-oriented:

- AI and LLM integrations are easier in Python.
- Trading and data-processing libraries are readily available.
- FastAPI provides strong support for REST APIs.
- Pydantic gives request and response validation.
- Python is practical for strategy prototyping and agent experimentation.
- The backend can directly host the agentic-AI module in Version 1.

## Alternatives Considered

### Spring Boot

Spring Boot would provide a strong backend architecture, type safety, and mature ecosystem. It was not selected for Version 1 because agentic-AI prototyping, data processing, and LLM integration are faster in Python.

Spring Boot may still be suitable for other portfolio or enterprise-oriented projects.

### Node.js / NestJS

NestJS provides a structured TypeScript backend and could pair well with React. It was not selected because the AI/trading/data side of the project benefits more from Python.

### Separate Python AI service plus backend in another language

Rejected for V1 due to additional complexity. A separate AI service may be considered later if the agent module grows independently.

## Consequences

### Positive

- fast AI and trading experimentation
- direct integration with Python data tooling
- simple REST API development
- straightforward local development
- good fit for Pydantic schemas and validation

### Negative

- runtime type safety is weaker than Java or TypeScript
- architecture discipline must be enforced through module structure and tests
- async/sync database choices must be handled carefully
- long-running background jobs require careful scheduler design

## Implementation Rules

- FastAPI routes must remain thin.
- Business logic must live in services/modules, not route functions.
- Pydantic schemas should define request and response contracts.
- SQLAlchemy should manage database persistence.
- Alembic should manage migrations.
- The scheduler must be initialized through backend lifecycle logic.
- External APIs must be wrapped behind adapters or clients.

## Related Documents

- `../system-overview.md`
- `../01_c4-model/c4-container.md`
- `../01_c4-model/c4-component.md`
- `../decisions.md`
