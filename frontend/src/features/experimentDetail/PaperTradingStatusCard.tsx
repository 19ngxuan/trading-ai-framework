import type { PaperStatus } from "../../types/paperStatus";

type PaperTradingStatusCardProps = {
  status: PaperStatus | undefined;
  isLoading: boolean;
};

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export function PaperTradingStatusCard({
  status,
  isLoading,
}: PaperTradingStatusCardProps) {
  if (isLoading) {
    return (
      <section className="panel wide-panel paper-status-panel">
        <h2>Paper Trading Status</h2>
        <p className="muted">Loading paper trading status...</p>
      </section>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <section className="panel wide-panel paper-status-panel">
      <div className="panel-header-row">
        <div>
          <h2>Paper Trading Status</h2>
          <p className="muted">{status.message}</p>
        </div>
        <span className="status-pill">{status.reasonCode}</span>
      </div>
      <dl className="detail-list compact-detail-list">
        <div>
          <dt>Scheduler</dt>
          <dd>{status.paperTradingSchedulerEnabled ? "Enabled" : "Disabled"}</dd>
        </div>
        <div>
          <dt>Alpaca Paper</dt>
          <dd>{status.alpacaPaperTradingEnabled ? "Enabled" : "Disabled"}</dd>
        </div>
        <div>
          <dt>Evaluation Time</dt>
          <dd>
            {status.dailyEvaluationTime} {status.timezone}
          </dd>
        </div>
        <div>
          <dt>Next Evaluation</dt>
          <dd>{formatDateTime(status.nextEligibleEvaluationTime)}</dd>
        </div>
        <div>
          <dt>Open Orders</dt>
          <dd>{status.openSubmittedOrdersCount}</dd>
        </div>
        <div>
          <dt>Last Broker Sync</dt>
          <dd>{formatDateTime(status.lastBrokerSyncTimestamp)}</dd>
        </div>
        <div>
          <dt>Last Paper Step</dt>
          <dd>
            {status.lastPaperExecutionStep
              ? `#${status.lastPaperExecutionStep.sequenceNumber} ${status.lastPaperExecutionStep.status}`
              : "-"}
          </dd>
        </div>
        <div>
          <dt>Current Slot Done</dt>
          <dd>{status.alreadyExecutedCurrentDueSlot ? "Yes" : "No"}</dd>
        </div>
      </dl>
    </section>
  );
}
