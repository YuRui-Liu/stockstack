import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { ACCESS_TOKEN_KEY, ApiError, UNAUTHORIZED_EVENT, apiRequest } from "./client";
import { server } from "../test/fixtures";

describe("API 认证会话", () => {
  it("旧请求的 401 不清除请求期间更新的新 token", async () => {
    let releaseResponse: (() => void) | undefined;
    let markRequestReceived: (() => void) | undefined;
    const requestReceived = new Promise<void>((resolve) => { markRequestReceived = resolve; });
    const waitForResponse = new Promise<void>((resolve) => { releaseResponse = resolve; });

    server.use(
      http.get("*/api/v1/products", async ({ request }) => {
        markRequestReceived?.();
        await waitForResponse;
        if (request.headers.get("Authorization") !== "Bearer old-token") {
          return HttpResponse.json({ message: "unexpected authorization" }, { status: 500 });
        }
        return HttpResponse.json(
          { code: "authentication_failed", message: "会话已失效", field_errors: {}, request_id: "old-request" },
          { status: 401 },
        );
      }),
    );

    let unauthorized = false;
    const handleUnauthorized = () => { unauthorized = true; };
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "old-token");
    const request = apiRequest("/api/v1/products").catch((error: unknown) => error);

    await requestReceived;
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "new-token");
    releaseResponse?.();

    const result = await request;
    expect(result).toBeInstanceOf(ApiError);
    expect((result as ApiError).status).toBe(401);
    expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBe("new-token");
    expect(unauthorized).toBe(false);
    window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
  });
});
