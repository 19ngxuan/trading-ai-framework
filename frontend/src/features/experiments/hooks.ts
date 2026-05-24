import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createExperiment,
  getExperiment,
  listExperiments,
  pauseExperiment,
  resumeExperiment,
  startExperiment,
  stopExperiment,
  type ListExperimentsParams,
} from "../../api/experimentsApi";
import { listExperimentEvents } from "../../api/eventsApi";
import { getMetrics, getPortfolioSnapshots } from "../../api/metricsApi";
import { getOptions } from "../../api/optionsApi";
import type {
  CreateExperimentPayload,
  ExperimentActionResponse,
  ExperimentStatus,
} from "../../types/experiment";

export const experimentKeys = {
  all: ["experiments"] as const,
  list: (params: ListExperimentsParams) =>
    [...experimentKeys.all, "list", params] as const,
  detail: (id: number) => [...experimentKeys.all, "detail", id] as const,
  metrics: (id: number) => [...experimentKeys.all, "metrics", id] as const,
  portfolioSnapshots: (id: number) =>
    [...experimentKeys.all, "portfolio-snapshots", id] as const,
  events: (id: number) => [...experimentKeys.all, "events", id] as const,
  options: ["options"] as const,
};

export function useExperiments(params: ListExperimentsParams = {}, poll = true) {
  return useQuery({
    queryKey: experimentKeys.list(params),
    queryFn: () => listExperiments(params),
    refetchInterval: poll ? 10_000 : false,
  });
}

export function useExperiment(id: number) {
  return useQuery({
    queryKey: experimentKeys.detail(id),
    queryFn: () => getExperiment(id),
    enabled: Number.isFinite(id),
    refetchInterval: (query) =>
      query.state.data?.experiment.status === "RUNNING" ? 5_000 : false,
  });
}

export function useMetrics(id: number, status?: ExperimentStatus) {
  return useQuery({
    queryKey: experimentKeys.metrics(id),
    queryFn: () => getMetrics(id, { limit: 500, offset: 0 }),
    enabled: Number.isFinite(id),
    refetchInterval: status === "RUNNING" ? 5_000 : false,
  });
}

export function usePortfolioSnapshots(id: number, status?: ExperimentStatus) {
  return useQuery({
    queryKey: experimentKeys.portfolioSnapshots(id),
    queryFn: () => getPortfolioSnapshots(id, { limit: 500, offset: 0 }),
    enabled: Number.isFinite(id),
    refetchInterval: status === "RUNNING" ? 5_000 : false,
  });
}

export function useExperimentEvents(id: number, status?: ExperimentStatus) {
  return useQuery({
    queryKey: experimentKeys.events(id),
    queryFn: () => listExperimentEvents(id, { limit: 50, offset: 0 }),
    enabled: Number.isFinite(id),
    refetchInterval: status === "RUNNING" ? 5_000 : false,
  });
}

export function useOptions() {
  return useQuery({
    queryKey: experimentKeys.options,
    queryFn: getOptions,
    staleTime: 60_000,
  });
}

function useActionMutation(
  mutationFn: (id: number) => Promise<ExperimentActionResponse>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: experimentKeys.all });
      void queryClient.invalidateQueries({ queryKey: experimentKeys.detail(id) });
      void queryClient.invalidateQueries({ queryKey: experimentKeys.metrics(id) });
      void queryClient.invalidateQueries({
        queryKey: experimentKeys.portfolioSnapshots(id),
      });
      void queryClient.invalidateQueries({ queryKey: experimentKeys.events(id) });
    },
  });
}

export function useExperimentActions() {
  return {
    start: useActionMutation(startExperiment),
    pause: useActionMutation(pauseExperiment),
    resume: useActionMutation(resumeExperiment),
    stop: useActionMutation(stopExperiment),
  };
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateExperimentPayload) => createExperiment(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: experimentKeys.all });
    },
  });
}
