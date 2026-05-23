import { useState } from "react";

import { errorMessage } from "../../components/ui/ErrorState";
import type { ExperimentStatus } from "../../types/experiment";
import { useExperimentActions } from "./hooks";

type ExperimentActionsProps = {
  experimentId: number;
  status: ExperimentStatus;
};

export function ExperimentActions({
  experimentId,
  status,
}: ExperimentActionsProps) {
  const actions = useExperimentActions();
  const [error, setError] = useState<string | null>(null);

  const run = async (action: "start" | "pause" | "resume" | "stop") => {
    setError(null);
    try {
      await actions[action].mutateAsync(experimentId);
    } catch (mutationError) {
      setError(errorMessage(mutationError));
    }
  };

  const isPending =
    actions.start.isPending ||
    actions.pause.isPending ||
    actions.resume.isPending ||
    actions.stop.isPending;

  return (
    <div className="action-stack">
      <div className="button-row">
        {status === "CREATED" && (
          <button disabled={isPending} onClick={() => void run("start")}>
            Start
          </button>
        )}
        {status === "RUNNING" && (
          <>
            <button disabled={isPending} onClick={() => void run("pause")}>
              Pause
            </button>
            <button disabled={isPending} onClick={() => void run("stop")}>
              Stop
            </button>
          </>
        )}
        {status === "PAUSED" && (
          <>
            <button disabled={isPending} onClick={() => void run("resume")}>
              Resume
            </button>
            <button disabled={isPending} onClick={() => void run("stop")}>
              Stop
            </button>
          </>
        )}
      </div>
      {error && <div className="inline-error">{error}</div>}
    </div>
  );
}
