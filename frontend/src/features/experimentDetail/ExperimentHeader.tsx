import { ExperimentStatusBadge } from "../../components/status/ExperimentStatusBadge";
import type { ExperimentDetail } from "../../types/experiment";
import { ExperimentActions } from "../experiments/ExperimentActions";

type ExperimentHeaderProps = {
  detail: ExperimentDetail;
};

export function ExperimentHeader({ detail }: ExperimentHeaderProps) {
  const { experiment } = detail;

  return (
    <div className="detail-header">
      <div>
        <p className="eyebrow">Experiment Detail</p>
        <h2>{experiment.name}</h2>
        <div className="meta-row">
          <ExperimentStatusBadge status={experiment.status} />
          <span>{experiment.strategyType}</span>
          <span>{experiment.mode}</span>
          <span>{experiment.assetSymbol}</span>
        </div>
      </div>
      <ExperimentActions
        experimentId={experiment.id}
        status={experiment.status}
      />
    </div>
  );
}
