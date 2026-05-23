import type { MetricSnapshot, PortfolioSnapshot } from "../../types/metrics";

type PerformanceChartPanelProps = {
  metrics: MetricSnapshot[];
  portfolioSnapshots: PortfolioSnapshot[];
};

type Point = {
  label: string;
  value: number;
};

function buildPath(points: Point[], width: number, height: number) {
  if (points.length === 0) return "";
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return points
    .map((point, index) => {
      const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
      const y = height - ((point.value - min) / span) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function LineChart({ points }: { points: Point[] }) {
  const width = 720;
  const height = 180;
  const path = buildPath(points, width, height);

  if (points.length === 0) {
    return <div className="chart-empty">No snapshot data available.</div>;
  }

  return (
    <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="3" />
    </svg>
  );
}

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
      <LineChart points={portfolioPoints} />
      <div className="section-header compact-header">
        <h3>Return</h3>
      </div>
      <LineChart points={returnPoints} />
    </section>
  );
}
