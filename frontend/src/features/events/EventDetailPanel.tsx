import type { SystemEvent } from "../../types/event";

type EventDetailPanelProps = {
  event: SystemEvent | null;
};

export function EventDetailPanel({ event }: EventDetailPanelProps) {
  return (
    <aside className="event-detail-panel">
      <h3>Event Details</h3>
      {event ? (
        <>
          <dl className="status-list">
            <div>
              <dt>Event ID</dt>
              <dd>{event.id}</dd>
            </div>
            <div>
              <dt>Execution Step</dt>
              <dd>{event.executionStepId ?? "-"}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{event.createdAt}</dd>
            </div>
          </dl>
          <pre className="json-block">
            {JSON.stringify(event.detailsJson ?? {}, null, 2)}
          </pre>
        </>
      ) : (
        <p className="muted">Select an event to inspect details.</p>
      )}
    </aside>
  );
}
