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
import { listExperimentBrokerSyncLogs } from "../../api/brokerSyncApi";
import { listExperimentEvents } from "../../api/eventsApi";
import { getMetrics, getPortfolioSnapshots } from "../../api/metricsApi";
import { listExperimentOrders } from "../../api/ordersApi";
import { getOptions } from "../../api/optionsApi";
import { getExperimentPaperStatus } from "../../api/paperStatusApi";
import { listExperimentTrades } from "../../api/tradesApi";
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
  orders: (id: number) => [...experimentKeys.all, "orders", id] as const,
  trades: (id: number) => [...experimentKeys.all, "trades", id] as const,
  brokerSyncLogs: (id: number) =>
    [...experimentKeys.all, "broker-sync-logs", id] as const,
  paperStatus: (id: number) => [...experimentKeys.all, "paper-status", id] as const,
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
    queryFn: () => getMetrics(id, { limit: 10000, offset: 0 }),
    enabled: Number.isFinite(id),
    refetchInterval: status === "RUNNING" ? 5_000 : false,
  });
}

export function usePortfolioSnapshots(id: number, status?: ExperimentStatus) {
  return useQuery({
    queryKey: experimentKeys.portfolioSnapshots(id),
    queryFn: () => getPortfolioSnapshots(id, { limit: 10000, offset: 0 }),
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

export function useExperimentOrders(id: number, status?: ExperimentStatus) {
  return useQuery({
    queryKey: experimentKeys.orders(id),
    queryFn: () => listExperimentOrders(id, { limit: 50, offset: 0 }),
    enabled: Number.isFinite(id),
    refetchInterval: status === "RUNNING" || status === "PAUSED" ? 5_000 : false,
  });
}

export function useExperimentTrades(id: number, status?: ExperimentStatus) {
  return useQuery({
    queryKey: experimentKeys.trades(id),
    queryFn: () => listExperimentTrades(id, { limit: 50, offset: 0 }),
    enabled: Number.isFinite(id),
    refetchInterval: status === "RUNNING" || status === "PAUSED" ? 5_000 : false,
  });
}

export function useExperimentBrokerSyncLogs(
  id: number,
  status?: ExperimentStatus,
) {
  return useQuery({
    queryKey: experimentKeys.brokerSyncLogs(id),
    queryFn: () => listExperimentBrokerSyncLogs(id, { limit: 50, offset: 0 }),
    enabled: Number.isFinite(id),
    refetchInterval: status === "RUNNING" || status === "PAUSED" ? 5_000 : false,
  });
}

export function useExperimentPaperStatus(
  id: number,
  mode?: string,
  status?: ExperimentStatus,
) {
  return useQuery({
    queryKey: experimentKeys.paperStatus(id),
    queryFn: () => getExperimentPaperStatus(id),
    enabled: Number.isFinite(id) && mode === "PAPER_TRADING",
    refetchInterval: status === "RUNNING" || status === "PAUSED" ? 5_000 : false,
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
      void queryClient.invalidateQueries({ queryKey: experimentKeys.orders(id) });
      void queryClient.invalidateQueries({ queryKey: experimentKeys.trades(id) });
      void queryClient.invalidateQueries({
        queryKey: experimentKeys.brokerSyncLogs(id),
      });
      void queryClient.invalidateQueries({ queryKey: experimentKeys.paperStatus(id) });
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
