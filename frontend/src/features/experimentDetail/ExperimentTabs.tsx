import { useState } from "react";

import type { ExperimentDetail } from "../../types/experiment";
import type { MetricSnapshot, PortfolioSnapshot } from "../../types/metrics";

type ExperimentTabsProps = {
  detail: ExperimentDetail;
  metrics: MetricSnapshot[];
  portfolioSnapshots: PortfolioSnapshot[];
};

type Tab = "overview" | "metrics" | "portfolio" | "config";

function formatValue(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isInteger(value) ? value : value.toFixed(4);
  return value;
}

export function ExperimentTabs({
  detail,
  metrics,
  portfolioSnapshots,
}: ExperimentTabsProps) {
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <section className="panel wide-panel">
      <div className="tab-list">
        <button
          className={tab === "overview" ? "tab-active" : undefined}
          onClick={() => setTab("overview")}
        >
          Overview
        </button>
        <button
          className={tab === "metrics" ? "tab-active" : undefined}
          onClick={() => setTab("metrics")}
        >
          Metrics
        </button>
        <button
          className={tab === "portfolio" ? "tab-active" : undefined}
          onClick={() => setTab("portfolio")}
        >
          Portfolio Snapshots
        </button>
        <button
          className={tab === "config" ? "tab-active" : undefined}
          onClick={() => setTab("config")}
        >
          Config
        </button>
      </div>

      {tab === "overview" && (
        <dl className="detail-list">
          <div>
            <dt>Initial Capital</dt>
            <dd>{detail.experiment.initialCapital}</dd>
          </div>
          <div>
            <dt>Date Range</dt>
            <dd>
              {detail.experiment.startDate} to {detail.experiment.endDate}
            </dd>
          </div>
          <div>
            <dt>Frequency</dt>
            <dd>{detail.experiment.tradingFrequency}</dd>
          </div>
          <div>
            <dt>Current Cash</dt>
            <dd>{detail.portfolio.cash}</dd>
          </div>
          <div>
            <dt>Position</dt>
            <dd>
              {detail.portfolio.positionSymbol ?? "-"}{" "}
              {detail.portfolio.positionQuantity ?? 0}
            </dd>
          </div>
        </dl>
      )}

      {tab === "metrics" && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Return</th>
                <th>P/L</th>
                <th>Trades</th>
                <th>Drawdown</th>
                <th>Buy and Hold</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((item) => (
                <tr key={item.timestamp}>
                  <td>{item.timestamp}</td>
                  <td>{formatValue(item.totalReturn)}</td>
                  <td>{formatValue(item.profitLoss)}</td>
                  <td>{formatValue(item.numberOfTrades)}</td>
                  <td>{formatValue(item.maxDrawdown)}</td>
                  <td>{formatValue(item.buyAndHoldReturn)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {metrics.length === 0 && <p className="muted">No metrics available.</p>}
        </div>
      )}

      {tab === "portfolio" && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Cash</th>
                <th>Position</th>
                <th>Market Value</th>
                <th>Total Value</th>
                <th>Price</th>
              </tr>
            </thead>
            <tbody>
              {portfolioSnapshots.map((item) => (
                <tr key={item.timestamp}>
                  <td>{item.timestamp}</td>
                  <td>{formatValue(item.cash)}</td>
                  <td>
                    {item.positionSymbol ?? "-"} {item.positionQuantity ?? 0}
                  </td>
                  <td>{formatValue(item.positionMarketValue)}</td>
                  <td>{formatValue(item.totalPortfolioValue)}</td>
                  <td>{formatValue(item.currentPrice)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {portfolioSnapshots.length === 0 && (
            <p className="muted">No portfolio snapshots available.</p>
          )}
        </div>
      )}

      {tab === "config" && (
        <dl className="detail-list">
          <div>
            <dt>Strategy Version</dt>
            <dd>{detail.strategyConfig.strategyVersion}</dd>
          </div>
          <div>
            <dt>Moving Average Window</dt>
            <dd>{detail.strategyConfig.movingAverageWindow ?? "-"}</dd>
          </div>
          <div>
            <dt>Position Sizing</dt>
            <dd>{detail.strategyConfig.positionSizingType ?? "-"}</dd>
          </div>
          <div>
            <dt>Fee Model</dt>
            <dd>{detail.experiment.feeModelType}</dd>
          </div>
          <div>
            <dt>Fee Value</dt>
            <dd>{detail.experiment.feeValue}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
