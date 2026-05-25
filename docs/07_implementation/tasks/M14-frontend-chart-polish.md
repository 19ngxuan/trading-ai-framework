# M14: Frontend Chart Polish

## Goal

Improve the existing lightweight SVG charts so performance and comparison data
are easier to interpret.

---

## Scope

- Add visible x/y axes, tick marks, tick labels, and axis titles.
- Include years in date labels.
- Keep charts responsive and proportionally scaled.
- Keep the existing custom SVG implementation.

---

## Out of Scope

- No backend changes.
- No API changes.
- No chart dependency such as Recharts, Chart.js, or D3.
- No fake data.
- No trading, simulation, broker, agent, scheduler, or market-data behavior changes.

---

## Acceptance Criteria

- Experiment detail charts show readable portfolio-value and return axes.
- Compare chart shows readable portfolio-value axes for multiple series.
- Empty charts still show axes and a clear empty-state message.
- Frontend build passes.
