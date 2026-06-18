import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { CreateExperimentDrawer } from "../features/experiments/CreateExperimentDrawer";
import { ExperimentSummaryTable } from "../features/experiments/ExperimentSummaryTable";
import { useExperiments, useOptions } from "../features/experiments/hooks";
import type {
  ExperimentMode,
  ExperimentStatus,
  StrategyType,
} from "../types/experiment";

export function ExperimentsPage() {
  const optionsQuery = useOptions();
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<ExperimentStatus | "">("");
  const [strategyType, setStrategyType] = useState<StrategyType | "">("");
  const [mode, setMode] = useState<ExperimentMode | "">("");
  const isCreateDrawerOpen = searchParams.get("create") === "1";

  const experimentsQuery = useExperiments(
    {
      status: status || undefined,
      strategyType: strategyType || undefined,
      mode: mode || undefined,
      limit: 50,
      offset: 0,
    },
    true,
  );

  const openCreateDrawer = () => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("create", "1");
      return next;
    });
  };

  const closeCreateDrawer = () => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("create");
      return next;
    });
  };

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Experiments</p>
          <h2>Experiment List</h2>
        </div>
        <button className="button-primary" onClick={openCreateDrawer} type="button">
          Create Experiment
        </button>
      </div>

      <section className="panel wide-panel">
        <div className="filter-row">
          <label>
            Status
            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as ExperimentStatus | "")
              }
            >
              <option value="">All</option>
              {optionsQuery.data?.experimentStatuses.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Strategy
            <select
              value={strategyType}
              onChange={(event) =>
                setStrategyType(event.target.value as StrategyType | "")
              }
            >
              <option value="">All</option>
              {optionsQuery.data?.strategies.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Mode
            <select
              value={mode}
              onChange={(event) =>
                setMode(event.target.value as ExperimentMode | "")
              }
            >
              <option value="">All</option>
              {optionsQuery.data?.modes.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {experimentsQuery.isLoading && <LoadingState />}
      {experimentsQuery.isError && <ErrorState error={experimentsQuery.error} />}
      {experimentsQuery.data && (
        <section className="panel wide-panel">
          <ExperimentSummaryTable experiments={experimentsQuery.data.items} />
        </section>
      )}
      <CreateExperimentDrawer
        isOpen={isCreateDrawerOpen}
        onClose={closeCreateDrawer}
      />
    </div>
  );
}
