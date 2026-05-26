import type { PaginatedResponse } from "./api";

export type OrderMode = "SIMULATED" | "PAPER_BROKER";
export type BrokerName = "ALPACA" | "NONE";
export type OrderSide = "BUY" | "SELL";
export type OrderType = "MARKET";
export type OrderStatus =
  | "CREATED"
  | "SUBMITTED"
  | "FILLED"
  | "REJECTED"
  | "FAILED"
  | "CANCELLED";

export type Order = {
  id: number;
  executionStepId: number;
  experimentId: number;
  riskCheckId: number;
  mode: OrderMode;
  brokerName: BrokerName | null;
  brokerOrderId: string | null;
  symbol: string;
  side: OrderSide;
  quantity: number;
  orderType: OrderType;
  status: OrderStatus;
  submittedAt: string | null;
  filledAt: string | null;
  averageFillPrice: number | null;
  errorMessage: string | null;
  createdAt: string;
};

export type PaginatedOrders = PaginatedResponse<Order>;
