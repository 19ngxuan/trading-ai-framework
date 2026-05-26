import type { PaginatedResponse } from "./api";
import type { BrokerName } from "./order";

export type BrokerSyncStatus = "SUCCESS" | "FAILED" | "MISMATCH";

export type BrokerSyncLog = {
  id: number;
  executionStepId: number;
  experimentId: number;
  timestamp: string;
  brokerName: BrokerName;
  syncStatus: BrokerSyncStatus;
  brokerCash: number | null;
  localCash: number | null;
  brokerPositionsJson: Record<string, unknown> | null;
  localPositionsJson: Record<string, unknown> | null;
  mismatchDetailsJson: Record<string, unknown> | null;
  errorMessage: string | null;
  createdAt: string;
};

export type PaginatedBrokerSyncLogs = PaginatedResponse<BrokerSyncLog>;
