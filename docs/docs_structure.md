# Documentation Structure

```text
/docs
├── agent
│   ├── instructions.md
│   ├── workflow.md
│   ├── guardrails.md
│   ├── definition-of-done.md
│   └── change-process.md
│
├── architecture
│   ├── system-overview.md
│   ├── c4-context.md
│   ├── c4-container.md
│   ├── c4-component.md
│   ├── decisions.md
│   └── adr
│       ├── ADR-001-modular-monolith.md
│       ├── ADR-002-fastapi-backend.md
│       ├── ADR-003-postgresql.md
│       ├── ADR-004-agent-as-strategy.md
│       └── ADR-005-risk-engine-before-execution.md
│
├── domain
│   ├── entities.md
│   ├── workflows.md
│   └── business-rules.md
│
├── api
│   ├── api-spec.md
│   └── openapi.yaml
│
├── database
│   ├── schema.dbml
│   └── migrations.md
│
├── frontend
│   ├── ui-routes.md
│   └── components.md
│
├── backend
│   ├── module-structure.md
│   └── service-contracts.md
│
└── implementation
    ├── coding-standards.md
    ├── task-breakdown.md
    ├── acceptance-criteria.md
    └── tasks
        ├── M0-setup.md
        ├── M1-domain-model.md
        ├── M2-experiment-api.md
        └── M3-buy-and-hold-simulation.md