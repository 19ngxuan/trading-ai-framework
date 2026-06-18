# M19: Interactive Charts and KPI Consistency

## Goal

Replace static portfolio/equity SVG charts where appropriate with interactive
chart components and align experiment-detail KPI values with the latest
persisted portfolio snapshots.

## Implemented Scope

- Frontend-only chart/KPI consistency work.
- Interactive portfolio, return, and comparison line charts.
- Chart data comes from persisted `PortfolioSnapshot` and `MetricSnapshot`
  records.
- Compare snapshots are loaded after the user runs comparison.
- `SvgLineChart` remains available for simple local SVG charts.
- Backend metric calculations, trading behavior, and persistence behavior are
  unchanged.

## Boundaries

- No frontend metric recalculation.
- No fake chart data.
- No backend execution changes.
- No schema migration.

