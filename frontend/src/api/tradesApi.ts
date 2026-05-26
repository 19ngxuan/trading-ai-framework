import { apiGet, queryString } from "./client";
import type { ListParams } from "../types/api";
import type { PaginatedTrades } from "../types/trade";

export function listExperimentTrades(
  experimentId: number,
  params: ListParams = {},
): Promise<PaginatedTrades> {
  return apiGet<PaginatedTrades>(
    `/experiments/${experimentId}/trades${queryString(params)}`,
  );
}
