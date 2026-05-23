export type ErrorResponse = {
  errorCode: string;
  message: string;
  details: Record<string, unknown>;
};

export type PaginatedResponse<T> = {
  items: T[];
  limit: number;
  offset: number;
  total: number;
};

export type ListParams = {
  limit?: number;
  offset?: number;
};
