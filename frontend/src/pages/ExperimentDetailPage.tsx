import { useParams } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ExperimentHeader } from "../features/experimentDetail/ExperimentHeader";
import { ExperimentKpiRow } from "../features/experimentDetail/ExperimentKpiRow";
import { ExperimentTabs } from "../features/experimentDetail/ExperimentTabs";
import { PerformanceChartPanel } from "../features/experimentDetail/PerformanceChartPanel";
import {
  useExperiment,
  useMetrics,
  usePortfolioSnapshots,
} from "../features/experiments/hooks";

export function ExperimentDetailPage() {
  const params = useParams();
  const experimentId = Number(params.experimentId);
  const detailQuery = useExperiment(experimentId);
  const status = detailQuery.data?.experiment.status;
  const metricsQuery = useMetrics(experimentId, status);
  const portfolioSnapshotsQuery = usePortfolioSnapshots(experimentId, status);

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

  const metrics = metricsQuery.data?.items ?? [];
  const portfolioSnapshots = portfolioSnapshotsQuery.data?.items ?? [];

  return (
    <div className="page-stack">
      <section className="panel wide-panel">
        <ExperimentHeader detail={detailQuery.data} />
      </section>
      <ExperimentKpiRow detail={detailQuery.data} />
      {(metricsQuery.isError || portfolioSnapshotsQuery.isError) && (
        <ErrorState error={metricsQuery.error ?? portfolioSnapshotsQuery.error} />
      )}
      <PerformanceChartPanel
        metrics={metrics}
        portfolioSnapshots={portfolioSnapshots}
      />
      <ExperimentTabs
        detail={detailQuery.data}
        metrics={metrics}
        portfolioSnapshots={portfolioSnapshots}
      />
    </div>
  );
}
