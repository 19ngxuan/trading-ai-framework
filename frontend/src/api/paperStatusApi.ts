import { apiGet } from "./client";
import type { PaperStatus } from "../types/paperStatus";

export function getExperimentPaperStatus(
  experimentId: number,
): Promise<PaperStatus> {
  return apiGet<PaperStatus>(`/experiments/${experimentId}/paper-status`);
}
