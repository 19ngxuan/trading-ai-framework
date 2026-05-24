import type { PortfolioSnapshot } from "../../types/metrics";

type Series = {
  experimentId: number;
  name: string;
  snapshots: PortfolioSnapshot[];
};

type ComparisonChartPanelProps = {
  series: Series[];
};

const colors = ["#245ca7", "#16845b", "#9d5a00", "#7c3aed", "#b42318"];

function buildPath(values: number[], width: number, height: number) {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export function ComparisonChartPanel({ series }: ComparisonChartPanelProps) {
  const drawableSeries = series
    .map((item) => ({
      ...item,
      values: item.snapshots
        .map((snapshot) => snapshot.totalPortfolioValue)
        .filter((value): value is number => value !== null),
    }))
    .filter((item) => item.values.length > 0);

  if (drawableSeries.length === 0) {
    return (
      <section className="panel wide-panel">
        <h2>Equity Curves</h2>
        <div className="chart-empty">No portfolio snapshots available.</div>
      </section>
    );
  }

  return (
    <section className="panel wide-panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Chart</p>
          <h2>Equity Curves</h2>
        </div>
      </div>
      <svg className="line-chart compare-chart" viewBox="0 0 640 220" role="img">
        {drawableSeries.map((item, index) => (
          <path
            key={item.experimentId}
            d={buildPath(item.values, 600, 180)}
            fill="none"
            stroke={colors[index % colors.length]}
            strokeWidth="3"
            transform="translate(20 20)"
          />
        ))}
      </svg>
      <div className="legend-row">
        {drawableSeries.map((item, index) => (
          <span key={item.experimentId}>
            <i style={{ background: colors[index % colors.length] }} />
            {item.name}
          </span>
        ))}
      </div>
    </section>
  );
}
