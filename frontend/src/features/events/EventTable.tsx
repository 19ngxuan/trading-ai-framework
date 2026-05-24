import type { SystemEvent } from "../../types/event";

type EventTableProps = {
  events: SystemEvent[];
  selectedEventId: number | null;
  onSelect: (event: SystemEvent) => void;
};

export function EventTable({
  events,
  selectedEventId,
  onSelect,
}: EventTableProps) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Level</th>
            <th>Experiment</th>
            <th>Type</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr
              key={event.id}
              className={[
                event.level === "ERROR" ? "event-row-error" : "",
                selectedEventId === event.id ? "event-row-selected" : "",
              ].join(" ")}
              onClick={() => onSelect(event)}
            >
              <td>{event.timestamp}</td>
              <td>
                <span className={`event-level event-level-${event.level.toLowerCase()}`}>
                  {event.level}
                </span>
              </td>
              <td>{event.experimentId}</td>
              <td>{event.eventType}</td>
              <td>{event.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {events.length === 0 && <p className="muted">No events match the filters.</p>}
    </div>
  );
}
