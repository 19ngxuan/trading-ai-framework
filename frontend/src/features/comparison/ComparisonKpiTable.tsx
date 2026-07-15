import type { CompareExperimentRow } from "../../types/comparison";

function formatNumber(value: number | null, digits = 4) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(digits);
}

function formatMoney(value: number | null) {
  if (value === null || value === undefined) return "-";
  return `$${value.toFixed(2)}`;
}

type ComparisonKpiTableProps = {
  rows: CompareExperimentRow[];
};

export function ComparisonKpiTable({ rows }: ComparisonKpiTableProps) {
  return (
    <section className="panel wide-panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Results</p>
          <h2>Comparison Table</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Experiment</th>
              <th>Status</th>
              <th>Portfolio</th>
              <th>Return</th>
              <th>P/L</th>
              <th>Trades</th>
              <th>Drawdown</th>
              <th>Benchmark Diff</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.experimentId}>
                <td className="comparison-experiment-cell">
                  <strong className="comparison-experiment-name" title={row.name}>
                    {row.name}
                  </strong>
                  <div className="muted">{row.strategyType}</div>
                </td>
                <td>{row.status}</td>
                <td>{formatMoney(row.latestPortfolioValue)}</td>
                <td>{formatNumber(row.totalReturn)}</td>
                <td>{formatMoney(row.profitLoss)}</td>
                <td>{row.numberOfTrades ?? "-"}</td>
                <td>{formatNumber(row.maxDrawdown)}</td>
                <td>{formatNumber(row.differenceToBenchmark)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
