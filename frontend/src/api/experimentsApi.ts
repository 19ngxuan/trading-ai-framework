import { apiGet, apiPost, queryString } from "./client";
import type {
  CreateExperimentPayload,
  CreateExperimentResponse,
  ExperimentActionResponse,
  ExperimentDetail,
  ExperimentMode,
  ExperimentStatus,
  PaginatedExperiments,
  StrategyType,
} from "../types/experiment";

export type ListExperimentsParams = {
  status?: ExperimentStatus;
  strategyType?: StrategyType;
  mode?: ExperimentMode;
  limit?: number;
  offset?: number;
};

export function listExperiments(
  params: ListExperimentsParams = {},
): Promise<PaginatedExperiments> {
  return apiGet<PaginatedExperiments>(`/experiments${queryString(params)}`);
}

export function getExperiment(id: number): Promise<ExperimentDetail> {
  return apiGet<ExperimentDetail>(`/experiments/${id}`);
}

export function createExperiment(
  payload: CreateExperimentPayload,
): Promise<CreateExperimentResponse> {
  return apiPost<CreateExperimentResponse, CreateExperimentPayload>(
    "/experiments",
    payload,
  );
}

export function startExperiment(id: number): Promise<ExperimentActionResponse> {
  return apiPost<ExperimentActionResponse>(`/experiments/${id}/start`);
}

export function pauseExperiment(id: number): Promise<ExperimentActionResponse> {
  return apiPost<ExperimentActionResponse>(`/experiments/${id}/pause`);
}

export function resumeExperiment(id: number): Promise<ExperimentActionResponse> {
  return apiPost<ExperimentActionResponse>(`/experiments/${id}/resume`);
}

export function stopExperiment(id: number): Promise<ExperimentActionResponse> {
  return apiPost<ExperimentActionResponse>(`/experiments/${id}/stop`);
}
