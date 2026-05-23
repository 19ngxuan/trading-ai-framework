import type { ExperimentDetail } from "../../types/experiment";

type ExperimentKpiRowProps = {
  detail: ExperimentDetail;
};

function money(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function percent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${(value * 100).toFixed(2)}%`;
}

export function ExperimentKpiRow({ detail }: ExperimentKpiRowProps) {
  const metrics = detail.latestMetrics;
  const portfolio = detail.portfolio;

  return (
    <div className="kpi-grid">
      <div className="kpi-card">
        <span>Portfolio Value</span>
        <strong>{money(portfolio.currentPortfolioValue)}</strong>
      </div>
      <div className="kpi-card">
        <span>Total Return</span>
        <strong>{percent(metrics?.totalReturn)}</strong>
      </div>
      <div className="kpi-card">
        <span>Profit/Loss</span>
        <strong>{money(metrics?.profitLoss)}</strong>
      </div>
      <div className="kpi-card">
        <span>Max Drawdown</span>
        <strong>{percent(metrics?.maxDrawdown)}</strong>
      </div>
      <div className="kpi-card">
        <span>Trades</span>
        <strong>{metrics?.numberOfTrades ?? "-"}</strong>
      </div>
      <div className="kpi-card">
        <span>Vs Buy and Hold</span>
        <strong>{percent(metrics?.differenceToBuyAndHold)}</strong>
      </div>
    </div>
  );
}
