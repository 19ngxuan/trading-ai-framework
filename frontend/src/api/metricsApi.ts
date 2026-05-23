import { apiGet, queryString } from "./client";
import type { ListParams } from "../types/api";
import type {
  PaginatedMetricSnapshots,
  PaginatedPortfolioSnapshots,
} from "../types/metrics";

export function getMetrics(
  experimentId: number,
  params: ListParams = {},
): Promise<PaginatedMetricSnapshots> {
  return apiGet<PaginatedMetricSnapshots>(
    `/experiments/${experimentId}/metrics${queryString(params)}`,
  );
}

export function getPortfolioSnapshots(
  experimentId: number,
  params: ListParams = {},
): Promise<PaginatedPortfolioSnapshots> {
  return apiGet<PaginatedPortfolioSnapshots>(
    `/experiments/${experimentId}/portfolio-snapshots${queryString(params)}`,
  );
}
