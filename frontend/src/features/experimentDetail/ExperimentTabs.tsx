import { useState } from "react";

import type {
  AgentDecisionInsight,
  ExperimentDetail,
} from "../../types/experiment";
import type { BrokerSyncLog } from "../../types/brokerSync";
import type { SystemEvent } from "../../types/event";
import type { MetricSnapshot, PortfolioSnapshot } from "../../types/metrics";
import type { Order } from "../../types/order";
import type { Trade } from "../../types/trade";

type ExperimentTabsProps = {
  detail: ExperimentDetail;
  metrics: MetricSnapshot[];
  portfolioSnapshots: PortfolioSnapshot[];
  events: SystemEvent[];
  orders: Order[];
  trades: Trade[];
  brokerSyncLogs: BrokerSyncLog[];
};

type Tab =
  | "overview"
  | "aiInsights"
  | "metrics"
  | "portfolio"
  | "orders"
  | "trades"
  | "brokerSync"
  | "events"
  | "config";

function formatValue(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isInteger(value) ? value : value.toFixed(4);
  return value;
}

function agentModeLabel(agentMode: ExperimentDetail["strategyConfig"]["agentMode"]) {
  if (agentMode === "PIPELINE") return "Multi Agent";
  if (agentMode === "SINGLE_AGENT") return "Single Agent";
  return "-";
}

function insightSummary(insight: AgentDecisionInsight) {
  const payload = insight.parsedOutputJson ?? {};
  const summaryKeys = ["summary", "rationale", "reason"];
  for (const key of summaryKeys) {
    const value = payload[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return insight.rawOutputText ?? "No summary available.";
}

function insightPrimarySignal(insight: AgentDecisionInsight) {
  const payload = insight.parsedOutputJson ?? {};
  for (const key of ["action", "signal", "riskLevel"]) {
    const value = payload[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return "-";
}

export function ExperimentTabs({
  detail,
  metrics,
  portfolioSnapshots,
  events,
  orders,
  trades,
  brokerSyncLogs,
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
        {detail.experiment.strategyType === "AGENTIC_AI" && (
          <button
            className={tab === "aiInsights" ? "tab-active" : undefined}
            onClick={() => setTab("aiInsights")}
          >
            AI Insights
          </button>
        )}
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
        <button
          className={tab === "orders" ? "tab-active" : undefined}
          onClick={() => setTab("orders")}
        >
          Orders
        </button>
        <button
          className={tab === "trades" ? "tab-active" : undefined}
          onClick={() => setTab("trades")}
        >
          Trades
        </button>
        <button
          className={tab === "brokerSync" ? "tab-active" : undefined}
          onClick={() => setTab("brokerSync")}
        >
          Broker Sync
        </button>
        <button
          className={tab === "events" ? "tab-active" : undefined}
          onClick={() => setTab("events")}
        >
          Events
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
          {detail.experiment.strategyType === "AGENTIC_AI" && (
            <>
              <div>
                <dt>AI Mode</dt>
                <dd>{agentModeLabel(detail.strategyConfig.agentMode)}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{detail.strategyConfig.modelName ?? "-"}</dd>
              </div>
              <div>
                <dt>Confidence Threshold</dt>
                <dd>{formatValue(detail.strategyConfig.confidenceThreshold)}</dd>
              </div>
            </>
          )}
        </dl>
      )}

      {tab === "aiInsights" && (
        <div className="page-stack">
          {detail.latestAgentDecisions.length === 0 ? (
            <p className="muted">No AI insight logs available yet.</p>
          ) : (
            detail.latestAgentDecisions.map((insight) => (
              <article key={insight.id} className="panel nested-panel">
                <div className="panel-header-row">
                  <div>
                    <h3>{insight.agentStepName.replace(/_/g, " ")}</h3>
                    <p className="muted">
                      {insight.agentName ?? "Agent"} · {insight.parsingStatus} ·{" "}
                      {new Date(insight.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <span className="status-pill">
                    {insightPrimarySignal(insight)}
                  </span>
                </div>
                <p>{insightSummary(insight)}</p>
              </article>
            ))
          )}
        </div>
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
            <dt>Moving Average Window</dt>
            <dd>{detail.strategyConfig.movingAverageWindow ?? "-"}</dd>
          </div>
          <div>
            <dt>Agent Mode</dt>
            <dd>{agentModeLabel(detail.strategyConfig.agentMode)}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{detail.strategyConfig.modelName ?? "-"}</dd>
          </div>
          <div>
            <dt>Confidence Threshold</dt>
            <dd>{formatValue(detail.strategyConfig.confidenceThreshold)}</dd>
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

      {tab === "orders" && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Created</th>
                <th>Status</th>
                <th>Mode</th>
                <th>Broker</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Type</th>
                <th>Broker Order</th>
                <th>Fill Price</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>{order.createdAt}</td>
                  <td>{order.status}</td>
                  <td>{order.mode}</td>
                  <td>{order.brokerName ?? "-"}</td>
                  <td>{order.side}</td>
                  <td>{formatValue(order.quantity)}</td>
                  <td>{order.orderType}</td>
                  <td>{order.brokerOrderId ?? "-"}</td>
                  <td>{formatValue(order.averageFillPrice)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {orders.length === 0 && <p className="muted">No orders available.</p>}
        </div>
      )}

      {tab === "trades" && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Order Value</th>
                <th>Portfolio After</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id}>
                  <td>{trade.timestamp}</td>
                  <td>{trade.symbol}</td>
                  <td>{trade.side}</td>
                  <td>{formatValue(trade.quantity)}</td>
                  <td>{formatValue(trade.price)}</td>
                  <td>{formatValue(trade.orderValue)}</td>
                  <td>{formatValue(trade.portfolioValueAfterTrade)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {trades.length === 0 && <p className="muted">No trades available.</p>}
        </div>
      )}

      {tab === "brokerSync" && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Status</th>
                <th>Broker</th>
                <th>Local Cash</th>
                <th>Message</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {brokerSyncLogs.map((log) => (
                <tr
                  key={log.id}
                  className={log.syncStatus === "FAILED" ? "event-row-error" : ""}
                >
                  <td>{log.timestamp}</td>
                  <td>{log.syncStatus}</td>
                  <td>{log.brokerName}</td>
                  <td>{formatValue(log.localCash)}</td>
                  <td>{log.errorMessage ?? "-"}</td>
                  <td>
                    {log.mismatchDetailsJson
                      ? JSON.stringify(log.mismatchDetailsJson)
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {brokerSyncLogs.length === 0 && (
            <p className="muted">No broker sync logs available.</p>
          )}
        </div>
      )}

      {tab === "events" && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Level</th>
                <th>Type</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr
                  key={event.id}
                  className={event.level === "ERROR" ? "event-row-error" : ""}
                >
                  <td>{event.timestamp}</td>
                  <td>{event.level}</td>
                  <td>{event.eventType}</td>
                  <td>{event.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {events.length === 0 && <p className="muted">No system events available.</p>}
        </div>
      )}
    </section>
  );
}
