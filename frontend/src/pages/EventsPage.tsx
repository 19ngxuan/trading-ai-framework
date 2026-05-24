import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listEvents } from "../api/eventsApi";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { EventDetailPanel } from "../features/events/EventDetailPanel";
import { EventFilters } from "../features/events/EventFilters";
import { EventTable } from "../features/events/EventTable";
import { useExperiments } from "../features/experiments/hooks";
import type { EventLevel, SystemEvent, SystemEventType } from "../types/event";

export function EventsPage() {
  const experimentsQuery = useExperiments({ limit: 100, offset: 0 }, true);
  const [experimentId, setExperimentId] = useState<number | "">("");
  const [level, setLevel] = useState<EventLevel | "">("");
  const [eventType, setEventType] = useState<SystemEventType | "">("");
  const [offset, setOffset] = useState(0);
  const [selectedEvent, setSelectedEvent] = useState<SystemEvent | null>(null);
  const limit = 25;

  const eventsQuery = useQuery({
    queryKey: ["events", experimentId, level, eventType, limit, offset],
    queryFn: () =>
      listEvents({
        experimentId: experimentId === "" ? undefined : experimentId,
        level: level || undefined,
        eventType: eventType || undefined,
        limit,
        offset,
      }),
    refetchInterval: 10_000,
  });

  const events = eventsQuery.data?.items ?? [];
  const canPageBack = offset > 0;
  const canPageForward = useMemo(
    () => Boolean(eventsQuery.data && offset + limit < eventsQuery.data.total),
    [eventsQuery.data, offset],
  );

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Events</p>
          <h2>System Event Log</h2>
        </div>
      </div>

      <EventFilters
        experiments={experimentsQuery.data?.items ?? []}
        experimentId={experimentId}
        level={level}
        eventType={eventType}
        onExperimentIdChange={(value) => {
          setExperimentId(value);
          setOffset(0);
        }}
        onLevelChange={(value) => {
          setLevel(value);
          setOffset(0);
        }}
        onEventTypeChange={(value) => {
          setEventType(value);
          setOffset(0);
        }}
      />

      {(eventsQuery.isLoading || experimentsQuery.isLoading) && <LoadingState />}
      {(eventsQuery.isError || experimentsQuery.isError) && (
        <ErrorState error={eventsQuery.error ?? experimentsQuery.error} />
      )}

      {eventsQuery.data && (
        <section className="panel wide-panel events-layout">
          <div>
            <EventTable
              events={events}
              selectedEventId={selectedEvent?.id ?? null}
              onSelect={setSelectedEvent}
            />
            <div className="pagination-row">
              <button
                disabled={!canPageBack}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </button>
              <span className="muted">
                {offset + 1}-{Math.min(offset + limit, eventsQuery.data.total)} of{" "}
                {eventsQuery.data.total}
              </span>
              <button
                disabled={!canPageForward}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </button>
            </div>
          </div>
          <EventDetailPanel event={selectedEvent} />
        </section>
      )}
    </div>
  );
}
