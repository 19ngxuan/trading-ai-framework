import { apiGet, queryString } from "./client";
import type { PaginatedAgentDecisionLogs } from "../types/agentDecisionLog";

export type ListAgentDecisionLogsParams = {
  limit?: number;
  offset?: number;
};

export function listExperimentAgentDecisionLogs(
  experimentId: number,
  params: ListAgentDecisionLogsParams = {},
): Promise<PaginatedAgentDecisionLogs> {
  return apiGet<PaginatedAgentDecisionLogs>(
    `/experiments/${experimentId}/agent-decision-logs${queryString(params)}`,
  );
}
