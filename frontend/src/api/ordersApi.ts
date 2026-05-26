import { apiGet, queryString } from "./client";
import type { ListParams } from "../types/api";
import type { PaginatedOrders } from "../types/order";

export function listExperimentOrders(
  experimentId: number,
  params: ListParams = {},
): Promise<PaginatedOrders> {
  return apiGet<PaginatedOrders>(
    `/experiments/${experimentId}/orders${queryString(params)}`,
  );
}
