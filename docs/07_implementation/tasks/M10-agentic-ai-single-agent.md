# M10: Agentic AI Single Agent

## Goal

Implement first single-agent AI strategy producing TradingDecision.

---

## Scope

- Implement AgenticAIStrategy wrapper
- Implement LLMClient abstraction
- Build prompt and input JSON
- Parse structured output
- Repair invalid output
- Fallback HOLD after failed repair
- Persist AgentDecisionLog

---

## Out of Scope

- No complex multi-agent pipeline
- No direct order execution by agent

---

## Relevant Docs

- docs/01_architecture/adr/ADR-004-agent-as-strategy.md
- docs/06_backend/service-contracts.md

---

## Acceptance Criteria

- Single agent returns TradingDecision
- AgentDecisionLog stores input/prompt/raw/parsed
- Invalid output repair path exists
- Risk Engine remains mandatory

---

## Test Requirements

- Output parser tests
- LLM mock tests
- Agent execution integration test

---

## Files Likely Affected

- backend/app/modules/agents/
- backend/app/modules/strategies/agentic_ai_strategy.py

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
