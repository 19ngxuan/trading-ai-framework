import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ExperimentHeader } from "../features/experimentDetail/ExperimentHeader";
import { ExperimentKpiRow } from "../features/experimentDetail/ExperimentKpiRow";
import { ExperimentTabs } from "../features/experimentDetail/ExperimentTabs";
import { PaperTradingStatusCard } from "../features/experimentDetail/PaperTradingStatusCard";
import { PerformanceChartPanel } from "../features/experimentDetail/PerformanceChartPanel";
import {
  useExperiment,
  useExperimentAgentDecisionLogs,
  useExperimentBrokerSyncLogs,
  useExperimentEvents,
  useExperimentOrders,
  useExperimentPaperStatus,
  useExperimentTrades,
  useMetrics,
  usePortfolioSnapshots,
} from "../features/experiments/hooks";
import type { MetricSnapshot, PortfolioSnapshot } from "../types/metrics";

function sortByTimestamp<T extends { timestamp: string }>(items: T[]) {
  return items
    .slice()
    .sort(
      (left, right) =>
        Date.parse(left.timestamp) - Date.parse(right.timestamp) ||
        left.timestamp.localeCompare(right.timestamp),
    );
}

function latestPortfolioValue(snapshots: PortfolioSnapshot[]) {
  const latest = snapshots
    .slice()
    .reverse()
    .find((snapshot) => snapshot.totalPortfolioValue !== null);
  return latest?.totalPortfolioValue ?? null;
}

export function ExperimentDetailPage() {
  const params = useParams();
  const experimentId = Number(params.experimentId);
  const detailQuery = useExperiment(experimentId);
  const status = detailQuery.data?.experiment.status;
  const metricsQuery = useMetrics(experimentId, status);
  const portfolioSnapshotsQuery = usePortfolioSnapshots(experimentId, status);
  const eventsQuery = useExperimentEvents(experimentId, status);
  const paperStatusQuery = useExperimentPaperStatus(
    experimentId,
    detailQuery.data?.experiment.mode,
    status,
  );
  const ordersQuery = useExperimentOrders(experimentId, status);
  const tradesQuery = useExperimentTrades(experimentId, status);
  const brokerSyncLogsQuery = useExperimentBrokerSyncLogs(experimentId, status);
  const agentDecisionLogsQuery = useExperimentAgentDecisionLogs(
    experimentId,
    detailQuery.data?.experiment.strategyType,
    status,
  );
  const metrics = useMemo<MetricSnapshot[]>(
    () => sortByTimestamp(metricsQuery.data?.items ?? []),
    [metricsQuery.data?.items],
  );
  const portfolioSnapshots = useMemo<PortfolioSnapshot[]>(
    () => sortByTimestamp(portfolioSnapshotsQuery.data?.items ?? []),
    [portfolioSnapshotsQuery.data?.items],
  );
  const displayedPortfolioValue = latestPortfolioValue(portfolioSnapshots);
  const dataError =
    metricsQuery.error ??
    portfolioSnapshotsQuery.error ??
    eventsQuery.error ??
    paperStatusQuery.error ??
    ordersQuery.error ??
    tradesQuery.error ??
    brokerSyncLogsQuery.error ??
    agentDecisionLogsQuery.error;

  if (!Number.isFinite(experimentId)) {
    return <ErrorState error={new Error("Invalid experiment id.")} />;
  }

  if (detailQuery.isLoading) {
    return <LoadingState label="Loading experiment..." />;
  }

  if (detailQuery.isError) {
    return <ErrorState error={detailQuery.error} />;
  }

  if (!detailQuery.data) {
    return <ErrorState error={new Error("Experiment was not found.")} />;
  }

  return (
    <div className="page-stack">
      <section className="panel wide-panel">
        <ExperimentHeader detail={detailQuery.data} />
      </section>
      <ExperimentKpiRow
        detail={detailQuery.data}
        portfolioValue={displayedPortfolioValue}
      />
      {dataError && <ErrorState error={dataError} />}
      <PaperTradingStatusCard
        status={paperStatusQuery.data}
        isLoading={paperStatusQuery.isLoading}
      />
      <PerformanceChartPanel
        metrics={metrics}
        portfolioSnapshots={portfolioSnapshots}
      />
      <ExperimentTabs
        detail={detailQuery.data}
        metrics={metrics}
        portfolioSnapshots={portfolioSnapshots}
        events={eventsQuery.data?.items ?? []}
        orders={ordersQuery.data?.items ?? []}
        trades={tradesQuery.data?.items ?? []}
        brokerSyncLogs={brokerSyncLogsQuery.data?.items ?? []}
        agentDecisionLogs={agentDecisionLogsQuery.data?.items ?? []}
        agentDecisionLogsLoading={agentDecisionLogsQuery.isLoading}
        agentDecisionLogsError={agentDecisionLogsQuery.error}
      />
    </div>
  );
}
