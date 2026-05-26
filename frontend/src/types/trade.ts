import type { PaginatedResponse } from "./api";
import type { OrderSide } from "./order";

export type Trade = {
  id: number;
  executionStepId: number;
  experimentId: number;
  orderId: number;
  timestamp: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  orderValue: number | null;
  fee: number | null;
  portfolioValueAfterTrade: number | null;
  createdAt: string;
};

export type PaginatedTrades = PaginatedResponse<Trade>;
