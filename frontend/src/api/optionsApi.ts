import { apiGet } from "./client";
import type { OptionsResponse } from "../types/experiment";

export function getOptions(): Promise<OptionsResponse> {
  return apiGet<OptionsResponse>("/options");
}
