import type { PaginatedResponse } from "./api";

export type MetricSnapshot = {
  timestamp: string;
  totalReturn: number | null;
  profitLoss: number | null;
  numberOfTrades: number | null;
  maxDrawdown: number | null;
  buyAndHoldReturn: number | null;
  differenceToBuyAndHold: number | null;
};

export type PortfolioSnapshot = {
  timestamp: string;
  cash: number;
  positionSymbol: string | null;
  positionQuantity: number | null;
  positionMarketValue: number | null;
  totalPortfolioValue: number | null;
  currentPrice: number | null;
};

export type PaginatedMetricSnapshots = PaginatedResponse<MetricSnapshot>;
export type PaginatedPortfolioSnapshots = PaginatedResponse<PortfolioSnapshot>;
