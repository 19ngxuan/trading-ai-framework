import { apiPost } from "./client";
import type {
  CompareExperimentsRequest,
  CompareExperimentsResponse,
} from "../types/comparison";

export function compareExperiments(
  payload: CompareExperimentsRequest,
): Promise<CompareExperimentsResponse> {
  return apiPost<CompareExperimentsResponse, CompareExperimentsRequest>(
    "/experiments/compare",
    payload,
  );
}
