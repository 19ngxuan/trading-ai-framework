import { apiGet, queryString } from "./client";
import type { ListParams } from "../types/api";
import type { PaginatedBrokerSyncLogs } from "../types/brokerSync";

export function listExperimentBrokerSyncLogs(
  experimentId: number,
  params: ListParams = {},
): Promise<PaginatedBrokerSyncLogs> {
  return apiGet<PaginatedBrokerSyncLogs>(
    `/experiments/${experimentId}/broker-sync-logs${queryString(params)}`,
  );
}
