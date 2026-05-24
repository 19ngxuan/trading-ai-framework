import type { PaginatedResponse } from "./api";

export type EventLevel = "INFO" | "WARNING" | "ERROR";

export type SystemEventType =
  | "EXPERIMENT_CREATED"
  | "EXPERIMENT_STARTED"
  | "EXPERIMENT_PAUSED"
  | "EXPERIMENT_RESUMED"
  | "EXPERIMENT_STOPPED"
  | "EXPERIMENT_COMPLETED"
  | "EXPERIMENT_FAILED"
  | "MARKET_DATA_MISSING"
  | "STRATEGY_DECISION_CREATED"
  | "RISK_LIMIT_TRIGGERED"
  | "ORDER_SUBMITTED"
  | "ORDER_FILLED"
  | "ORDER_FAILED"
  | "BROKER_SYNC_FAILED"
  | "BROKER_STATE_MISMATCH"
  | "LLM_OUTPUT_INVALID"
  | "LLM_REPAIR_ATTEMPTED"
  | "FALLBACK_HOLD_USED";

export type SystemEvent = {
  id: number;
  experimentId: number;
  executionStepId: number | null;
  timestamp: string;
  level: EventLevel;
  eventType: SystemEventType;
  message: string;
  detailsJson: Record<string, unknown> | null;
  createdAt: string;
};

export type ListEventsParams = {
  experimentId?: number;
  level?: EventLevel;
  eventType?: SystemEventType;
  limit?: number;
  offset?: number;
};

export type PaginatedSystemEvents = PaginatedResponse<SystemEvent>;
