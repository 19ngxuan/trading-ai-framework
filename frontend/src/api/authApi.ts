import { apiGet, apiPost } from "./client";
import type { AuthMeResponse, LoginRequest, LoginResponse } from "../types/auth";

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return apiPost<LoginResponse, LoginRequest>("/auth/login", payload);
}

export function getCurrentAuth(): Promise<AuthMeResponse> {
  return apiGet<AuthMeResponse>("/auth/me");
}
