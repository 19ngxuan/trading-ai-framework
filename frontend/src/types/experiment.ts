import type { PaginatedResponse } from "./api";
import type { MetricSnapshot } from "./metrics";

export type ExperimentMode =
  | "HISTORICAL_SIMULATION"
  | "LIVE_SIMULATION"
  | "PAPER_TRADING";

export type StrategyType =
  | "BUY_AND_HOLD"
  | "MOVING_AVERAGE"
  | "AGENTIC_AI"
  | "OPENING_RANGE_BREAKOUT"
  | "PAPER_TRADING_SMOKE_TEST";

export type ExperimentStatus =
  | "CREATED"
  | "RUNNING"
  | "PAUSED"
  | "STOPPED"
  | "COMPLETED"
  | "FAILED";

export type TradingFrequency =
  | "DAILY"
  | "WEEKLY"
  | "MONTHLY"
  | "INTRADAY_5_MIN"
  | "TEST_1_MIN";
export type FeeModelType = "NONE" | "FIXED" | "PERCENTAGE";
export type AgentMode = "SINGLE_AGENT" | "PIPELINE";
export type PositionSizingType =
  | "ALL_IN"
  | "FIXED_CASH"
  | "PERCENT_OF_PORTFOLIO"
  | "FIXED_QUANTITY";
export type OrderStatus =
  | "CREATED"
  | "SUBMITTED"
  | "FILLED"
  | "REJECTED"
  | "FAILED"
  | "CANCELLED";

export type LastTrade = {
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  timestamp: string;
};

export type Experiment = {
  id: number;
  name: string;
  mode: ExperimentMode;
  strategyType: StrategyType;
  assetSymbol: string;
  status: ExperimentStatus;
  initialCapital: number;
  startDate: string;
  endDate: string;
  tradingFrequency: TradingFrequency;
  feeModelType: FeeModelType;
  feeValue: number;
  createdAt: string;
  updatedAt: string;
};

export type StrategyConfig = {
  id: number;
  experimentId: number;
  strategyType: StrategyType;
  strategyVersion: string;
  movingAverageWindow: number | null;
  positionSizingType: PositionSizingType | null;
  positionSizingValue: number | null;
  agentMode: AgentMode | null;
  modelName: string | null;
  confidenceThreshold: number | null;
  parametersJson: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
};

export type Portfolio = {
  id: number;
  experimentId: number;
  cash: number;
  positionSymbol: string | null;
  positionQuantity: number | null;
  currentPrice: number | null;
  currentPositionValue: number | null;
  currentPortfolioValue: number | null;
  updatedAt: string;
};

export type ExperimentSummary = {
  id: number;
  name: string;
  mode: ExperimentMode;
  strategyType: StrategyType;
  assetSymbol: string;
  status: ExperimentStatus;
  currentPortfolioValue: number | null;
  totalReturn: number | null;
  profitLoss: number | null;
  numberOfTrades: number | null;
  maxDrawdown: number | null;
  lastTrade: LastTrade | null;
  latestAgentDecisions: Record<string, unknown>[];
};

export type ExperimentDetail = {
  experiment: Experiment;
  strategyConfig: StrategyConfig;
  portfolio: Portfolio;
  latestMetrics: MetricSnapshot | null;
  latestAgentDecisions: Record<string, unknown>[];
};

export type PaginatedExperiments = PaginatedResponse<ExperimentSummary>;

export type OptionsResponse = {
  assets: string[];
  modes: ExperimentMode[];
  strategies: StrategyType[];
  experimentStatuses: ExperimentStatus[];
  tradingFrequencies: TradingFrequency[];
  feeModelTypes: FeeModelType[];
  agentModes: AgentMode[];
  orderStatuses: OrderStatus[];
};

export type StrategyConfigInput = {
  strategyVersion: string;
  movingAverageWindow: number | null;
  positionSizingType: PositionSizingType | null;
  positionSizingValue: number | null;
  agentMode: AgentMode | null;
  modelName: string | null;
  confidenceThreshold: number | null;
  parametersJson: Record<string, unknown>;
};

export type CreateExperimentPayload = {
  name: string;
  mode: ExperimentMode;
  strategyType: StrategyType;
  assetSymbol: string;
  initialCapital: number;
  startDate: string;
  endDate: string;
  tradingFrequency: TradingFrequency;
  feeModelType: FeeModelType;
  feeValue: number;
  strategyConfig: StrategyConfigInput;
};

export type CreateExperimentResponse = {
  experiment: Experiment;
  portfolio: Portfolio;
};

export type ExperimentActionResponse = {
  experimentId: number;
  status: ExperimentStatus;
  message: string | null;
};
