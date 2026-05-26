import type {
  ExperimentMode,
  ExperimentStatus,
  StrategyType,
  TradingFrequency,
} from "./experiment";

export type ExecutionStepStatus = "RUNNING" | "COMPLETED" | "SKIPPED" | "FAILED";
export type TriggerType = "HISTORICAL" | "SCHEDULED" | "MANUAL";

export type PaperExecutionStepSummary = {
  id: number;
  status: ExecutionStepStatus;
  triggerType: TriggerType;
  sequenceNumber: number;
  scheduledFor: string | null;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
  createdAt: string;
};

export type PaperStatus = {
  experimentId: number;
  experimentStatus: ExperimentStatus;
  mode: ExperimentMode;
  strategyType: StrategyType;
  tradingFrequency: TradingFrequency;
  assetSymbol: string;
  supportedByPaperScheduler: boolean;
  paperTradingSchedulerEnabled: boolean;
  alpacaPaperTradingEnabled: boolean;
  dailyEvaluationTime: string;
  timezone: string;
  currentDueSlot: string | null;
  nextEligibleEvaluationTime: string | null;
  alreadyExecutedCurrentDueSlot: boolean;
  openSubmittedOrdersCount: number;
  lastBrokerSyncTimestamp: string | null;
  lastPaperExecutionStep: PaperExecutionStepSummary | null;
  reasonCode: string;
  message: string;
};
