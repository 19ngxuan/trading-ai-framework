import { SvgLineChart } from "../../components/charts/SvgLineChart";
import type { MetricSnapshot, PortfolioSnapshot } from "../../types/metrics";

type PerformanceChartPanelProps = {
  metrics: MetricSnapshot[];
  portfolioSnapshots: PortfolioSnapshot[];
};

export function PerformanceChartPanel({
  metrics,
  portfolioSnapshots,
}: PerformanceChartPanelProps) {
  const portfolioPoints = portfolioSnapshots
    .filter((snapshot) => snapshot.totalPortfolioValue !== null)
    .map((snapshot) => ({
      label: snapshot.timestamp,
      value: snapshot.totalPortfolioValue ?? 0,
    }));
  const returnPoints = metrics
    .filter((snapshot) => snapshot.totalReturn !== null)
    .map((snapshot) => ({
      label: snapshot.timestamp,
      value: snapshot.totalReturn ?? 0,
    }));

  return (
    <section className="panel wide-panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Performance</p>
          <h3>Portfolio Value</h3>
        </div>
      </div>
      <SvgLineChart
        emptyMessage="No snapshot data available."
        series={[
          {
            id: "portfolio-value",
            name: "Portfolio Value",
            color: "#245ca7",
            points: portfolioPoints,
          },
        ]}
        height={480}
        valueFormat="currency"
        xAxisLabel="Date"
        yAxisLabel="Portfolio Value"
      />
      <div className="section-header compact-header">
        <h3>Return</h3>
      </div>
      <SvgLineChart
        emptyMessage="No metric data available."
        series={[
          {
            id: "return",
            name: "Return",
            color: "#16845b",
            points: returnPoints,
          },
        ]}
        height={440}
        valueFormat="percent"
        xAxisLabel="Date"
        yAxisLabel="Return"
      />
    </section>
  );
}
