import type { EventLevel, SystemEventType } from "../../types/event";
import type { ExperimentSummary } from "../../types/experiment";

type EventFiltersProps = {
  experiments: ExperimentSummary[];
  experimentId: number | "";
  level: EventLevel | "";
  eventType: SystemEventType | "";
  onExperimentIdChange: (value: number | "") => void;
  onLevelChange: (value: EventLevel | "") => void;
  onEventTypeChange: (value: SystemEventType | "") => void;
};

const levels: EventLevel[] = ["INFO", "WARNING", "ERROR"];
const eventTypes: SystemEventType[] = [
  "EXPERIMENT_CREATED",
  "EXPERIMENT_STARTED",
  "EXPERIMENT_PAUSED",
  "EXPERIMENT_RESUMED",
  "EXPERIMENT_STOPPED",
  "EXPERIMENT_COMPLETED",
  "EXPERIMENT_FAILED",
  "MARKET_DATA_MISSING",
  "RISK_LIMIT_TRIGGERED",
  "ORDER_SUBMITTED",
  "ORDER_FILLED",
  "ORDER_FAILED",
  "BROKER_SYNC_FAILED",
  "BROKER_STATE_MISMATCH",
  "LLM_OUTPUT_INVALID",
  "LLM_REPAIR_ATTEMPTED",
  "FALLBACK_HOLD_USED",
];

export function EventFilters({
  experiments,
  experimentId,
  level,
  eventType,
  onExperimentIdChange,
  onLevelChange,
  onEventTypeChange,
}: EventFiltersProps) {
  return (
    <section className="panel wide-panel">
      <div className="filter-row">
        <label>
          Experiment
          <select
            value={experimentId}
            onChange={(event) =>
              onExperimentIdChange(
                event.target.value === "" ? "" : Number(event.target.value),
              )
            }
          >
            <option value="">All</option>
            {experiments.map((experiment) => (
              <option key={experiment.id} value={experiment.id}>
                {experiment.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Level
          <select
            value={level}
            onChange={(event) => onLevelChange(event.target.value as EventLevel | "")}
          >
            <option value="">All</option>
            {levels.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label>
          Event Type
          <select
            value={eventType}
            onChange={(event) =>
              onEventTypeChange(event.target.value as SystemEventType | "")
            }
          >
            <option value="">All</option>
            {eventTypes.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}
