import type { ExperimentSummary } from "../../types/experiment";

type DashboardKpiCardsProps = {
  experiments: ExperimentSummary[];
};

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${(value * 100).toFixed(2)}%`;
}

export function DashboardKpiCards({ experiments }: DashboardKpiCardsProps) {
  const running = experiments.filter((item) => item.status === "RUNNING").length;
  const completed = experiments.filter((item) => item.status === "COMPLETED").length;
  const failed = experiments.filter((item) => item.status === "FAILED").length;
  const best = experiments
    .filter((item) => item.totalReturn !== null)
    .sort((a, b) => (b.totalReturn ?? 0) - (a.totalReturn ?? 0))[0];

  return (
    <div className="kpi-grid">
      <div className="kpi-card">
        <span>Running</span>
        <strong>{running}</strong>
      </div>
      <div className="kpi-card">
        <span>Completed</span>
        <strong>{completed}</strong>
      </div>
      <div className="kpi-card">
        <span>Failed</span>
        <strong>{failed}</strong>
      </div>
      <div className="kpi-card">
        <span>Best Return</span>
        <strong>{best ? formatPercent(best.totalReturn) : "-"}</strong>
      </div>
    </div>
  );
}
