import { apiGet, queryString } from "./client";
import type { ListEventsParams, PaginatedSystemEvents } from "../types/event";

export function listEvents(
  params: ListEventsParams = {},
): Promise<PaginatedSystemEvents> {
  return apiGet<PaginatedSystemEvents>(`/events${queryString(params)}`);
}

export function listExperimentEvents(
  experimentId: number,
  params: Omit<ListEventsParams, "experimentId"> = {},
): Promise<PaginatedSystemEvents> {
  return apiGet<PaginatedSystemEvents>(
    `/experiments/${experimentId}/events${queryString(params)}`,
  );
}
