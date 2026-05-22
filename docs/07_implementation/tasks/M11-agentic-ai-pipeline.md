# M11: Agentic AI Pipeline

## Goal

Implement simple pipeline-agent mode with multiple logged agent steps.

---

## Scope

- Implement MarketAnalystAgent
- Implement TradingDecisionAgent
- Implement AgentRiskManager
- Pass intermediate outputs between steps
- Store AgentDecisionLog per step
- Return final TradingDecision

---

## Out of Scope

- No large multi-agent swarm
- No memory/reflection framework unless explicitly approved

---

## Relevant Docs

- docs/02_domain/workflows.md
- docs/06_backend/service-contracts.md

---

## Acceptance Criteria

- PIPELINE mode produces final TradingDecision
- Each pipeline step has AgentDecisionLog
- System Risk Engine still validates final decision

---

## Test Requirements

- Pipeline agent tests with mocked LLM
- Log persistence tests

---

## Files Likely Affected

- backend/app/modules/agents/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
