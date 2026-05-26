# Task Breakdown

## 1. Purpose

This document defines the implementation roadmap for Trading Lab.

Tasks are grouped into milestones. Each milestone has a dedicated task file under `docs/07_implementation/tasks/`.

Implementation should proceed incrementally. Do not start agentic AI or broker execution before the simulation core and audit model are stable.

---

## 2. Milestones

| Milestone | Task File | Goal |
|---|---|---|
| M0 | `tasks/M0-setup.md` | Repository, backend, frontend, database, and Docker setup |
| M1 | `tasks/M1-domain-model.md` | Domain model, SQLAlchemy models, Alembic migrations |
| M2 | `tasks/M2-experiment-api.md` | Experiment creation, status transitions, options API |
| M3 | `tasks/M3-buy-and-hold-simulation.md` | First historical simulation with Buy and Hold |
| M4 | `tasks/M4-moving-average-strategy.md` | 200-day Moving Average strategy |
| M5 | `tasks/M5-metrics-and-snapshots.md` | Portfolio snapshots and metrics calculation |
| M6 | `tasks/M6-dashboard-and-detail-ui.md` | Dashboard, create experiment, and detail UI |
| M7 | `tasks/M7-scheduler-and-run-next-step.md` | Scheduler and manual execution step support |
| M8 | `tasks/M8-alpaca-market-data.md` | Alpaca Market Data integration |
| M9 | `tasks/M9-alpaca-paper-trading.md` | Alpaca Paper Trading integration |
| M10 | `tasks/M10-agentic-ai-single-agent.md` | Single-agent AI strategy |
| M11 | `tasks/M11-agentic-ai-pipeline.md` | Pipeline-agent strategy |
| M12 | `tasks/M12-compare-and-events-ui.md` | Compare screen and Events UI |
| M13 | `tasks/M13-testing-hardening-readme.md` | Configurable position sizing and regression coverage |
| M14 | `tasks/M14-frontend-chart-polish.md` | Frontend SVG chart axes and responsive proportional sizing |
| M15 | `tasks/M15-hardening-documentation.md` | Documentation, API contract, runbook, and safety-boundary hardening |
| M16 | `tasks/M16-opening-range-breakout.md` | Opening Range Breakout historical simulation |
| M17 | `tasks/M17-alpaca-intraday-market-data.md` | Alpaca intraday market data for Opening Range Breakout |
| M18 | `tasks/M18-trading-calendar-intraday-orb.md` | Trading calendar and early-close support for intraday ORB |
| M20 | `tasks/M20-live-paper-trading.md` | Scheduled paper trading and broker order-status sync |
| M22 | `tasks/M22-paper-trading-smoke-test.md` | Diagnostics-only paper trading smoke-test strategy |
| M23 Spike | `tasks/M23-alpaca-xetra-paper-trading-spike.md` | Spike to verify Alpaca Xetra/European ETF paper-trading feasibility |
| M23 | `tasks/M23-rule-based-paper-trading.md` | Scheduled paper trading for rule-based Moving Average and Opening Range Breakout |

---

## 3. Recommended Implementation Order

1. M0 Setup
2. M1 Domain Model + Database
3. M2 Experiment API
4. M3 Buy and Hold Simulation
5. M4 Moving Average Strategy
6. M5 Metrics + Snapshots
7. M6 Dashboard + Detail UI
8. M7 Scheduler + Run Next Step
9. M8 Alpaca Market Data
10. M9 Alpaca Paper Trading
11. M10 Agentic AI Single Agent
12. M11 Agentic AI Pipeline
13. M12 Compare + Events UI
14. M13 Configurable Position Sizing
15. M14 Frontend Chart Polish
16. M15 Hardening + Documentation
17. M16 Opening Range Breakout
18. M17 Alpaca Intraday Market Data for ORB
19. M18 Trading Calendar + Early-Close Support
20. M20 Live Paper Trading Scheduler + Broker Sync
21. M22 Paper Trading Smoke-Test Strategy
22. M23 Alpaca Xetra Paper Trading Spike
23. M23 Rule-Based Paper Trading

---

## 4. Minimal V1a MVP

The smallest useful MVP is:

- M0
- M1
- M2
- M3
- M4
- M5
- M6

This produces a usable simulation system with two strategies, metrics, and UI visibility.

---

## 5. Implementation Rule

Each task must follow:

1. Read relevant docs.
2. Confirm task scope.
3. Implement only the scoped behavior.
4. Add or update tests.
5. Update docs if contracts or behavior changed.
6. Verify no architecture rule is violated.
