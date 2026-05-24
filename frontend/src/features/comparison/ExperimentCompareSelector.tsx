import type { ExperimentSummary } from "../../types/experiment";

type ExperimentCompareSelectorProps = {
  experiments: ExperimentSummary[];
  selectedIds: number[];
  benchmarkId: number | "";
  onSelectedIdsChange: (ids: number[]) => void;
  onBenchmarkIdChange: (id: number | "") => void;
};

export function ExperimentCompareSelector({
  experiments,
  selectedIds,
  benchmarkId,
  onSelectedIdsChange,
  onBenchmarkIdChange,
}: ExperimentCompareSelectorProps) {
  function toggleExperiment(id: number) {
    const nextIds = selectedIds.includes(id)
      ? selectedIds.filter((selectedId) => selectedId !== id)
      : [...selectedIds, id];
    onSelectedIdsChange(nextIds);
    if (benchmarkId !== "" && !nextIds.includes(benchmarkId)) {
      onBenchmarkIdChange("");
    }
  }

  return (
    <section className="panel wide-panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Compare</p>
          <h2>Select Experiments</h2>
        </div>
        <label className="compact-select">
          Benchmark
          <select
            value={benchmarkId}
            onChange={(event) =>
              onBenchmarkIdChange(
                event.target.value === "" ? "" : Number(event.target.value),
              )
            }
          >
            <option value="">None</option>
            {experiments
              .filter((experiment) => selectedIds.includes(experiment.id))
              .map((experiment) => (
                <option key={experiment.id} value={experiment.id}>
                  {experiment.name}
                </option>
              ))}
          </select>
        </label>
      </div>

      <div className="selection-grid">
        {experiments.map((experiment) => (
          <label key={experiment.id} className="selection-item">
            <input
              type="checkbox"
              checked={selectedIds.includes(experiment.id)}
              onChange={() => toggleExperiment(experiment.id)}
            />
            <span>
              <strong>{experiment.name}</strong>
              <small>
                {experiment.strategyType} / {experiment.status}
              </small>
            </span>
          </label>
        ))}
      </div>
      {selectedIds.length < 2 && (
        <p className="muted">Select at least two experiments to compare.</p>
      )}
    </section>
  );
}
