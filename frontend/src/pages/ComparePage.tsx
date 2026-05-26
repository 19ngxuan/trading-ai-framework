import { useMemo, useState } from "react";
import { useMutation, useQueries } from "@tanstack/react-query";

import { compareExperiments } from "../api/comparisonApi";
import { getPortfolioSnapshots } from "../api/metricsApi";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ComparisonChartPanel } from "../features/comparison/ComparisonChartPanel";
import { ComparisonKpiTable } from "../features/comparison/ComparisonKpiTable";
import { ExperimentCompareSelector } from "../features/comparison/ExperimentCompareSelector";
import { useExperiments } from "../features/experiments/hooks";
import type { PortfolioSnapshot } from "../types/metrics";

function sortSnapshots(items: PortfolioSnapshot[]) {
  return items
    .slice()
    .sort(
      (left, right) =>
        Date.parse(left.timestamp) - Date.parse(right.timestamp) ||
        left.timestamp.localeCompare(right.timestamp),
    );
}

export function ComparePage() {
  const experimentsQuery = useExperiments({ limit: 100, offset: 0 }, true);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [comparedIds, setComparedIds] = useState<number[]>([]);
  const [benchmarkId, setBenchmarkId] = useState<number | "">("");

  const compareMutation = useMutation({
    mutationFn: () =>
      compareExperiments({
        experimentIds: selectedIds,
        benchmarkExperimentId: benchmarkId === "" ? null : benchmarkId,
      }),
    onSuccess: () => {
      setComparedIds(selectedIds.slice());
    },
  });

  const snapshotQueries = useQueries({
    queries: comparedIds.map((id) => ({
      queryKey: ["compare", "portfolio-snapshots", id],
      queryFn: () => getPortfolioSnapshots(id, { limit: 10000, offset: 0 }),
      enabled: comparedIds.length >= 2 && compareMutation.isSuccess,
    })),
  });

  const experiments = experimentsQuery.data?.items ?? [];
  const selectedExperimentNames = useMemo(
    () => new Map(experiments.map((experiment) => [experiment.id, experiment.name])),
    [experiments],
  );
  const chartSeries = comparedIds.map((id, index) => ({
    experimentId: id,
    name: selectedExperimentNames.get(id) ?? `Experiment ${id}`,
    snapshots: sortSnapshots(snapshotQueries[index]?.data?.items ?? []),
  }));

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Compare</p>
          <h2>Experiment Comparison</h2>
        </div>
        <button
          disabled={selectedIds.length < 2 || compareMutation.isPending}
          onClick={() => compareMutation.mutate()}
        >
          Compare Selected
        </button>
      </div>

      {experimentsQuery.isLoading && <LoadingState />}
      {experimentsQuery.isError && <ErrorState error={experimentsQuery.error} />}
      {experimentsQuery.data && experiments.length === 0 && (
        <EmptyState title="No experiments" detail="Create experiments before comparing." />
      )}
      {experimentsQuery.data && experiments.length > 0 && (
        <ExperimentCompareSelector
          experiments={experiments}
          selectedIds={selectedIds}
          benchmarkId={benchmarkId}
          onSelectedIdsChange={setSelectedIds}
          onBenchmarkIdChange={setBenchmarkId}
        />
      )}

      {compareMutation.isError && <ErrorState error={compareMutation.error} />}
      {compareMutation.isPending && <LoadingState label="Comparing experiments..." />}
      {compareMutation.data && (
        <>
          <ComparisonKpiTable rows={compareMutation.data.items} />
          <ComparisonChartPanel series={chartSeries} />
        </>
      )}
    </div>
  );
}
