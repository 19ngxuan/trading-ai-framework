import type { ErrorResponse } from "../types/api";

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  errorCode: string;
  details: Record<string, unknown>;
  status: number;

  constructor(status: number, error: ErrorResponse) {
    super(error.message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = error.errorCode;
    this.details = error.details;
  }
}

function buildUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ErrorResponse;
    return new ApiError(response.status, body);
  } catch {
    return new ApiError(response.status, {
      errorCode: "API_ERROR",
      message: `API request failed with status ${response.status}`,
      details: {},
    });
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(buildUrl(path));

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<TResponse, TPayload = undefined>(
  path: string,
  payload?: TPayload,
): Promise<TResponse> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers:
      payload === undefined ? undefined : { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json() as Promise<TResponse>;
}

export function queryString(params: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const value = searchParams.toString();
  return value ? `?${value}` : "";
}
