import type { ErrorResponse, LoginRequest, LoginResponse } from "./types";

export const ACCESS_TOKEN_KEY = "stockstack_access_token";
export const UNAUTHORIZED_EVENT = "stockstack:unauthorized";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const apiBaseUrl = configuredBaseUrl.replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly response: ErrorResponse,
  ) {
    super(response.message);
    this.name = "ApiError";
  }
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (!value || typeof value !== "object") return false;
  const response = value as Partial<ErrorResponse>;
  return (
    typeof response.code === "string" &&
    typeof response.message === "string" &&
    typeof response.request_id === "string" &&
    !!response.field_errors &&
    typeof response.field_errors === "object"
  );
}

function clearUnauthorizedSession(requestToken: string | null) {
  if (!requestToken || sessionStorage.getItem(ACCESS_TOKEN_KEY) !== requestToken) return;
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);

  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  const body: unknown = await response.json().catch(() => undefined);

  if (!response.ok) {
    if (response.status === 401) clearUnauthorizedSession(token);
    const errorResponse: ErrorResponse = isErrorResponse(body)
      ? body
      : {
          code: "unexpected_error",
          message: "服务暂时不可用，请稍后重试",
          field_errors: {},
          request_id: response.headers.get("x-request-id") ?? "",
        };
    throw new ApiError(response.status, errorResponse);
  }

  return body as T;
}

export function login(credentials: LoginRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}
