import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const physicalSchema = {
  product_type: "physical",
  version: 1,
  active: true,
  fields: [
    { key: "weight_kg", label: "重量（千克）", control: "number", data_type: "number", required: true, minimum: 0 },
    { key: "specification", label: "规格", control: "text", data_type: "string", required: true, max_length: 100 },
    { key: "shipping_template", label: "物流模板", control: "select", data_type: "string", required: true, options: ["standard", "cold_chain"] },
  ],
} as const;

export const virtualSchema = {
  product_type: "virtual",
  version: 1,
  active: true,
  fields: [
    { key: "validity_days", label: "有效期（天）", control: "number", data_type: "integer", required: true, minimum: 1 },
    { key: "verification_method", label: "核销方式", control: "select", data_type: "string", required: true, options: ["code", "qr", "manual"] },
    { key: "redemption_instructions", label: "兑换说明", control: "textarea", data_type: "string", required: true, max_length: 500 },
  ],
} as const;

export const creativeSchema = {
  product_type: "creative",
  version: 1,
  active: true,
  fields: [
    { key: "asset_type", label: "素材类型", control: "select", data_type: "string", required: true, options: ["image", "video", "html"] },
    { key: "dimensions", label: "投放尺寸", control: "text", data_type: "string", required: true, pattern: "^[1-9][0-9]*x[1-9][0-9]*$" },
    { key: "file_url", label: "文件地址", control: "text", data_type: "string", required: true, format: "http-url" },
  ],
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
  attributes: {
    weight_kg: 0.5,
    specification: "标准款",
    shipping_template: "standard",
  },
  schema_version: 1,
  version: 3,
  images: [
    { kind: "main", url: "/uploads/example.png", sort_order: 0, size_bytes: 1024, mime_type: "image/png" },
  ],
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

    return HttpResponse.json({
      access_token: "test-access-token",
      token_type: "bearer",
      expires_in: 3600,
    });
  }),
];

export const server = setupServer(...apiHandlers);
