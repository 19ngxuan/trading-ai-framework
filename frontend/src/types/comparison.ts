import type {
  ExperimentMode,
  ExperimentStatus,
  StrategyType,
} from "./experiment";

export type CompareExperimentsRequest = {
  experimentIds: number[];
  benchmarkExperimentId?: number | null;
};

export type CompareExperimentRow = {
  experimentId: number;
  name: string;
  mode: ExperimentMode;
  strategyType: StrategyType;
  status: ExperimentStatus;
  assetSymbol: string;
  latestPortfolioValue: number | null;
  totalReturn: number | null;
  profitLoss: number | null;
  numberOfTrades: number | null;
  maxDrawdown: number | null;
  benchmarkReturn: number | null;
  differenceToBenchmark: number | null;
};

export type CompareExperimentsResponse = {
  benchmarkExperimentId: number | null;
  items: CompareExperimentRow[];
};
