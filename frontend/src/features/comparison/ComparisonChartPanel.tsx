import { SvgLineChart } from "../../components/charts/SvgLineChart";
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

export function ComparisonChartPanel({ series }: ComparisonChartPanelProps) {
  const drawableSeries = series
    .map((item) => ({
      ...item,
      points: item.snapshots
        .filter((snapshot) => snapshot.totalPortfolioValue !== null)
        .map((snapshot) => ({
          label: snapshot.timestamp,
          value: snapshot.totalPortfolioValue ?? 0,
        })),
    }))
    .filter((item) => item.points.length > 0);

  if (drawableSeries.length === 0) {
    return (
      <section className="panel wide-panel">
        <h2>Equity Curves</h2>
        <SvgLineChart
          className="compare-chart"
          emptyMessage="No portfolio snapshots available."
          height={560}
          series={[]}
          valueFormat="currency"
          xAxisLabel="Date"
          yAxisLabel="Portfolio Value"
        />
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
      <SvgLineChart
        className="compare-chart"
        emptyMessage="No portfolio snapshots available."
        height={560}
        series={drawableSeries.map((item, index) => ({
          id: item.experimentId,
          name: item.name,
          color: colors[index % colors.length],
          points: item.points,
        }))}
        valueFormat="currency"
        xAxisLabel="Date"
        yAxisLabel="Portfolio Value"
      />
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
