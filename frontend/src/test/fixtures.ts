import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const physicalSchema = {
  product_type: "physical",
  version: 1,
  schema: {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    type: "object",
    properties: {
      weight_kg: { type: "number", minimum: 0, title: "重量（千克）" },
      specification: { type: "string", maxLength: 100, title: "规格" },
      shipping_template: { enum: ["standard", "cold_chain"], title: "物流模板" },
    },
    required: ["weight_kg", "specification", "shipping_template"],
    additionalProperties: false,
  },
} as const;

export const virtualSchema = {
  product_type: "virtual",
  version: 1,
  schema: {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    type: "object",
    properties: {
      validity_days: { type: "integer", minimum: 1, title: "有效期（天）" },
      verification_method: { enum: ["code", "qr", "manual"], title: "核销方式" },
      redemption_instructions: { type: "string", maxLength: 500, title: "兑换说明" },
    },
    required: ["validity_days", "verification_method", "redemption_instructions"],
    additionalProperties: false,
  },
} as const;

export const creativeSchema = {
  product_type: "creative",
  version: 1,
  schema: {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    type: "object",
    properties: {
      asset_type: { enum: ["image", "video", "html"], title: "素材类型" },
      dimensions: { type: "string", pattern: "^[1-9][0-9]*x[1-9][0-9]*$", title: "投放尺寸" },
      file_url: { type: "string", format: "http-url", title: "文件地址" },
    },
    required: ["asset_type", "dimensions", "file_url"],
    additionalProperties: false,
  },
} as const;

export const penalizedProduct = {
  id: "0198d72e-6700-7000-8000-000000000001",
  title: "处罚中的示例商品",
  short_title: "处罚示例",
  description_html: "<p>完整商品响应样例</p>",
  price_amount: "99.00",
  stock: 12,
  product_type: "physical",
  status: "penalized",
  delivery_method: "ems",
  return_rule: "seven_days",
  attributes: { weight_kg: 0.5, specification: "标准款", shipping_template: "standard" },
  schema_version: 1,
  version: 3,
  images: [{ kind: "main", url: "/uploads/example.png", sort_order: 0, size_bytes: 1024, mime_type: "image/png" }],
  created_at: "2026-08-21T08:00:00Z",
  updated_at: "2026-08-21T09:00:00Z",
} as const;

export const apiHandlers = [
  http.post("*/api/v1/auth/login", async ({ request }) => {
    const credentials = (await request.json()) as Record<string, unknown>;
    if (credentials.username !== "admin" || credentials.password !== "secret") {
      return HttpResponse.json(
        { code: "authentication_failed", message: "账号或密码错误", field_errors: {}, request_id: "test-login-error" },
        { status: 401 },
      );
    }
    return HttpResponse.json({ access_token: "test-access-token", token_type: "bearer", expires_in: 3600 });
  }),
];

export const server = setupServer(...apiHandlers);
