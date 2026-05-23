import { Link } from "react-router-dom";

import { ExperimentStatusBadge } from "../../components/status/ExperimentStatusBadge";
import { EmptyState } from "../../components/ui/EmptyState";
import type { ExperimentSummary } from "../../types/experiment";
import { ExperimentActions } from "./ExperimentActions";

type ExperimentSummaryTableProps = {
  experiments: ExperimentSummary[];
  compact?: boolean;
};

function formatMoney(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${(value * 100).toFixed(2)}%`;
}

export function ExperimentSummaryTable({
  experiments,
  compact = false,
}: ExperimentSummaryTableProps) {
  if (experiments.length === 0) {
    return (
      <EmptyState
        title="No experiments yet."
        detail="Create an experiment to start collecting simulation results."
      />
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Strategy</th>
            <th>Status</th>
            {!compact && <th>Mode</th>}
            <th>Portfolio</th>
            <th>Return</th>
            <th>P/L</th>
            {!compact && <th>Drawdown</th>}
            <th>Trades</th>
            <th>Last Trade</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {experiments.map((experiment) => (
            <tr key={experiment.id}>
              <td>
                <Link to={`/experiments/${experiment.id}`}>{experiment.name}</Link>
                <div className="muted">{experiment.assetSymbol}</div>
              </td>
              <td>{experiment.strategyType}</td>
              <td>
                <ExperimentStatusBadge status={experiment.status} />
              </td>
              {!compact && <td>{experiment.mode}</td>}
              <td>{formatMoney(experiment.currentPortfolioValue)}</td>
              <td>{formatPercent(experiment.totalReturn)}</td>
              <td>{formatMoney(experiment.profitLoss)}</td>
              {!compact && <td>{formatPercent(experiment.maxDrawdown)}</td>}
              <td>{experiment.numberOfTrades ?? "-"}</td>
              <td>
                {experiment.lastTrade
                  ? `${experiment.lastTrade.side} ${experiment.lastTrade.quantity} @ ${formatMoney(
                      experiment.lastTrade.price,
                    )}`
                  : "-"}
              </td>
              <td>
                <ExperimentActions
                  experimentId={experiment.id}
                  status={experiment.status}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
