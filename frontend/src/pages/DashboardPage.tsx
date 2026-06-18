import { Link } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { DashboardKpiCards } from "../features/dashboard/DashboardKpiCards";
import { ExperimentSummaryTable } from "../features/experiments/ExperimentSummaryTable";
import { useExperiments } from "../features/experiments/hooks";

export function DashboardPage() {
  const experimentsQuery = useExperiments({ limit: 5, offset: 0 }, true);

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h2>Experiment Overview</h2>
        </div>
        <Link className="button-link" to="/experiments?create=1">
          Create Experiment
        </Link>
      </div>
      {experimentsQuery.isLoading && <LoadingState />}
      {experimentsQuery.isError && <ErrorState error={experimentsQuery.error} />}
      {experimentsQuery.data && (
        <>
          <DashboardKpiCards experiments={experimentsQuery.data.items} />
          <section className="panel wide-panel">
            <div className="section-header">
              <h3>Recent Experiments</h3>
              <Link to="/experiments">View all</Link>
            </div>
            <ExperimentSummaryTable
              compact
              experiments={experimentsQuery.data.items}
            />
          </section>
        </>
      )}
    </div>
  );
}
