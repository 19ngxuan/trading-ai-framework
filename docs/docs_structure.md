# Documentation Structure

The numbered folder structure is canonical. Older unnumbered paths such as
`docs/api`, `docs/backend`, `docs/frontend`, `docs/database`, and `docs/agent`
must not be used.

```text
/docs
├── 01_architecture
│   ├── 01_c4-model
│   │   ├── c4-context.md
│   │   ├── c4-container.md
│   │   ├── c4-component.md
│   │   └── c4.dsl
│   ├── 02_adr
│   │   ├── ADR-001-modular-monolith.md
│   │   └── ADR-010-jsonb-for-flexible-parameters.md
│   ├── decisions.md
│   └── system-overview.md
├── 02_domain
├── 03_database
├── 04_api
├── 05_backend
├── 06_frontend
├── 07_implementation
│   └── tasks
│       ├── M0-setup.md
│       ├── ...
│       ├── M13-testing-hardening-readme.md
│       ├── M14-frontend-chart-polish.md
│       └── M15-hardening-documentation.md
├── 08_agent_instructions
└── docs_structure.md
```
