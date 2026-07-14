import type { AgentDecisionLog } from "../../types/agentDecisionLog";

type AgentDecisionLogPanelProps = {
  logs: AgentDecisionLog[];
  isLoading: boolean;
  error: Error | null;
};

const STAGE_ORDER = [
  "FETCH_DATA",
  "TECHNICAL_ANALYST",
  "FUNDAMENTAL_ANALYST",
  "SENTIMENT_ANALYST",
  "RISK_MANAGER",
  "PORTFOLIO_MANAGER",
];

type AgentDecisionLogGroup = {
  executionStepId: number;
  logs: AgentDecisionLog[];
};

function formatLabel(value: string | null | undefined) {
  if (!value) return "-";
  return value.replace(/_/g, " ");
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleString();
}

function formatPercent(value: unknown) {
  if (typeof value !== "number") return null;
  return `${Math.round(value * 100)}%`;
}

function stringField(payload: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}

function numberField(payload: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "number") return value;
  }
  return null;
}

function booleanField(payload: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "boolean") return value;
  }
  return null;
}

function nestedRecord(
  payload: Record<string, unknown> | null,
  key: string,
): Record<string, unknown> | null {
  const value = payload?.[key];
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function eventContext(log: AgentDecisionLog) {
  const direct = nestedRecord(log.inputJson, "eventContext");
  if (direct) return direct;
  const context = nestedRecord(log.inputJson, "context");
  return nestedRecord(context, "eventContext");
}

function auditRows(payload: Record<string, unknown>) {
  const action = stringField(payload, ["finalAction", "action", "signal"]);
  const tradeIntent = stringField(payload, ["tradeIntent"]);
  const primaryDriver = stringField(payload, ["primaryDriver"]);
  const targetExposurePct = numberField(payload, ["targetExposurePct"]);
  const confidence = numberField(payload, ["confidence"]);
  const newInformation = booleanField(payload, ["newInformation"]);
  const fallbackReason = stringField(payload, ["fallbackReason", "reason"]);
  return [
    ["Action", action],
    ["Trade Intent", tradeIntent],
    ["Target Exposure", formatPercent(targetExposurePct)],
    ["Confidence", formatPercent(confidence)],
    ["Primary Driver", primaryDriver],
    [
      "New Information",
      newInformation === null ? null : newInformation ? "Yes" : "No",
    ],
    ["Fallback / Reason", fallbackReason],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");
}

function summaryText(log: AgentDecisionLog) {
  const payload = log.parsedOutputJson ?? {};
  return (
    stringField(payload, ["rationale", "summary", "reason"]) ??
    log.rawOutputText ??
    "No rationale available."
  );
}

function modeLabel(mode: AgentDecisionLog["agentMode"]) {
  return mode === "PIPELINE" ? "Multi Agent" : "Single Agent";
}

function stageSortIndex(stageName: string) {
  const index = STAGE_ORDER.indexOf(stageName);
  return index === -1 ? STAGE_ORDER.length : index;
}

function groupAgentLogs(logs: AgentDecisionLog[]): AgentDecisionLogGroup[] {
  const groups = new Map<number, AgentDecisionLog[]>();
  for (const log of logs) {
    const group = groups.get(log.executionStepId) ?? [];
    group.push(log);
    groups.set(log.executionStepId, group);
  }
  return Array.from(groups, ([executionStepId, groupLogs]) => ({
    executionStepId,
    logs: groupLogs.slice().sort((left, right) => {
      const stageDelta =
        stageSortIndex(left.agentStepName) - stageSortIndex(right.agentStepName);
      if (stageDelta !== 0) return stageDelta;
      return (
        Date.parse(left.createdAt) - Date.parse(right.createdAt) ||
        left.id - right.id
      );
    }),
  }));
}

function groupTimestamp(logs: AgentDecisionLog[]) {
  const first = logs[0];
  return (
    formatDateTime(first.startedAt) ??
    formatDateTime(first.scheduledFor) ??
    formatDateTime(first.createdAt)
  );
}

function EvaluationStepHeader({ logs }: { logs: AgentDecisionLog[] }) {
  const first = logs[0];
  const stepLabel = first.executionStepSequenceNumber ?? first.executionStepId;
  return (
    <div className="agent-log-step-header">
      <div>
        <h3>Evaluation Step {stepLabel}</h3>
        <p className="muted">{groupTimestamp(logs)}</p>
      </div>
      <div className="agent-log-chip-row">
        {first.triggerType && (
          <span className="status-pill secondary-pill">{first.triggerType}</span>
        )}
        {first.executionStepStatus && (
          <span className="status-pill">{first.executionStepStatus}</span>
        )}
      </div>
    </div>
  );
}

export function AgentDecisionLogPanel({
  logs,
  isLoading,
  error,
}: AgentDecisionLogPanelProps) {
  if (isLoading) {
    return <p className="muted">Loading agent decision logs...</p>;
  }

  if (error) {
    return <p className="muted">Agent decision logs could not be loaded.</p>;
  }

  if (logs.length === 0) {
    return <p className="muted">No agent decision logs available yet.</p>;
  }

  const groups = groupAgentLogs(logs);

  return (
    <div className="agent-log-list">
      {groups.map((group) => (
        <section key={group.executionStepId} className="agent-log-step-group">
          <EvaluationStepHeader logs={group.logs} />
          {group.logs.map((log) => {
            const payload = log.parsedOutputJson ?? {};
            const rows = auditRows(payload);
            const event = eventContext(log);
            return (
              <article key={log.id} className="agent-log-card">
                <div className="panel-header-row">
                  <div>
                    <h3>{formatLabel(log.agentStepName)}</h3>
                    <p className="muted">
                      {modeLabel(log.agentMode)} · {log.agentName ?? "Agent"} · Step{" "}
                      {log.executionStepSequenceNumber ?? log.executionStepId} ·{" "}
                      {new Date(log.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <div className="agent-log-chip-row">
                    <span className="status-pill">{log.parsingStatus}</span>
                    {log.triggerType && (
                      <span className="status-pill secondary-pill">
                        {log.triggerType}
                      </span>
                    )}
                  </div>
                </div>

                <p>{summaryText(log)}</p>

                {rows.length > 0 && (
                  <dl className="agent-audit-grid">
                    {rows.map(([label, value]) => (
                      <div key={label}>
                        <dt>{label}</dt>
                        <dd>{formatLabel(String(value))}</dd>
                      </div>
                    ))}
                  </dl>
                )}

                {event && (
                  <div className="agent-event-context">
                    <strong>Event Context</strong>
                    <p className="muted">
                      {stringField(event, ["headline", "title", "summary"]) ??
                        "Event-triggered agent run"}
                    </p>
                    <div className="agent-log-chip-row">
                      {stringField(event, ["eventType"]) && (
                        <span className="status-pill secondary-pill">
                          {formatLabel(stringField(event, ["eventType"]))}
                        </span>
                      )}
                      {stringField(event, ["severity"]) && (
                        <span className="status-pill secondary-pill">
                          {formatLabel(stringField(event, ["severity"]))}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                <details className="json-details">
                  <summary>Audit JSON</summary>
                  <pre>{JSON.stringify(payload, null, 2)}</pre>
                </details>
              </article>
            );
          })}
        </section>
      ))}
    </div>
  );
}
