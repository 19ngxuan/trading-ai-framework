import type { ExperimentStatus } from "../../types/experiment";

type ExperimentStatusBadgeProps = {
  status: ExperimentStatus;
};

export function ExperimentStatusBadge({ status }: ExperimentStatusBadgeProps) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{status}</span>;
}
