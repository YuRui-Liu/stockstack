import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { creativeSchema, penalizedProduct, physicalSchema, server, virtualSchema } from "../test/fixtures";
import ProductFormPage from "./ProductFormPage";

function fillCommonFields() {
  fireEvent.change(screen.getByLabelText("商品标题"), { target: { value: "新商品" } });
  fireEvent.change(screen.getByLabelText("短标题"), { target: { value: "新品" } });
  fireEvent.change(screen.getByLabelText("价格"), { target: { value: "19.90" } });
  fireEvent.change(screen.getByLabelText("库存"), { target: { value: "5" } });
  fireEvent.change(screen.getByLabelText("商品描述"), { target: { value: "描述" } });
}

describe("ProductFormPage", () => {
  it("创建时切换类型读取 active schema 并提交完整契约", async () => {
    let submitted: Record<string, unknown> | undefined;
    server.use(
      http.get("*/api/v1/product-schemas/:type/active", ({ params }) => HttpResponse.json(params.type === "virtual" ? virtualSchema : physicalSchema)),
      http.post("*/api/v1/products", async ({ request }) => {
        submitted = await request.json() as Record<string, unknown>;
        return HttpResponse.json({ ...penalizedProduct, ...submitted, id: "created", version: 1 }, { status: 201 });
      }),
    );
    render(<ProductFormPage initialImages={[{ kind: "main", url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }]} />);
    await screen.findByLabelText("重量（千克）");
    fireEvent.mouseDown(screen.getByLabelText("商品类型"));
    fireEvent.click(await screen.findByText("虚拟商品"));
    await screen.findByLabelText("核销方式");
    fillCommonFields();
    fireEvent.change(screen.getByLabelText("有效期（天）"), { target: { value: "30" } });
    fireEvent.mouseDown(screen.getByLabelText("核销方式"));
    fireEvent.click((await screen.findAllByText("code")).at(-1)!);
    fireEvent.change(screen.getByLabelText("兑换说明"), { target: { value: "输入兑换码" } });
    fireEvent.click(screen.getByRole("button", { name: "发布商品" }));

    await waitFor(() => expect(submitted).toMatchObject({
      title: "新商品", short_title: "新品", price_amount: "19.90", stock: 5,
      product_type: "virtual", schema_version: 1,
      attributes: { validity_days: 30, verification_method: "code", redemption_instructions: "输入兑换码" },
      images: [{ kind: "main", url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }],
    }));
  });

  it("快速切换类型时只采用最后选择类型的 schema", async () => {
    let releaseVirtual: (() => void) | undefined;
    const virtualWait = new Promise<void>((resolve) => { releaseVirtual = resolve; });
    server.use(http.get("*/api/v1/product-schemas/:type/active", async ({ params }) => {
      if (params.type === "virtual") await virtualWait;
      return HttpResponse.json(params.type === "creative" ? creativeSchema : params.type === "virtual" ? virtualSchema : physicalSchema);
    }));
    render(<ProductFormPage initialImages={[]} />);
    await screen.findByLabelText("重量（千克）");
    fireEvent.mouseDown(screen.getByLabelText("商品类型"));
    fireEvent.click((await screen.findAllByText("虚拟商品")).at(-1)!);
    fireEvent.mouseDown(screen.getByLabelText("商品类型"));
    fireEvent.click((await screen.findAllByText("创意商品")).at(-1)!);
    await screen.findByLabelText("素材类型");
    releaseVirtual?.();
    await waitFor(() => expect(screen.getByLabelText("素材类型")).toBeInTheDocument());
  });

  it("将服务端 field_errors 定位到动态字段", async () => {
    server.use(
      http.get("*/api/v1/product-schemas/physical/active", () => HttpResponse.json(physicalSchema)),
      http.post("*/api/v1/products", () => HttpResponse.json({ code: "validation_error", message: "请检查字段", field_errors: { "attributes.weight_kg": ["重量无效"] }, request_id: "field-error" }, { status: 422 })),
    );
    render(<ProductFormPage initialImages={[{ kind: "main", url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }]} />);
    await screen.findByLabelText("重量（千克）");
    fillCommonFields();
    fireEvent.change(screen.getByLabelText("重量（千克）"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("规格"), { target: { value: "标准" } });
    fireEvent.mouseDown(screen.getByLabelText("物流模板"));
    fireEvent.click((await screen.findAllByText("standard")).at(-1)!);
    fireEvent.click(screen.getByRole("button", { name: "发布商品" }));
    expect(await screen.findByText("重量无效")).toBeInTheDocument();
  });

  it("编辑时绑定详情 schema 版本、禁用类型并提示陈旧版本", async () => {
    let activeRequested = false;
    let updatePayload: Record<string, unknown> | undefined;
    server.use(
      http.get("*/api/v1/products/:id", () => HttpResponse.json(penalizedProduct)),
      http.get("*/api/v1/product-schemas/physical/1", () => HttpResponse.json(physicalSchema)),
      http.get("*/api/v1/product-schemas/physical/active", () => { activeRequested = true; return HttpResponse.json(physicalSchema); }),
      http.put("*/api/v1/products/:id", async ({ request }) => {
        updatePayload = await request.json() as Record<string, unknown>;
        return HttpResponse.json({ code: "version_conflict", message: "stale", field_errors: {}, request_id: "stale" }, { status: 409 });
      }),
    );
    render(<ProductFormPage productId={penalizedProduct.id} />);
    expect(await screen.findByLabelText("商品类型")).toBeDisabled();
    expect(screen.getByLabelText("重量（千克）")).toHaveValue("0.5");
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("刷新");
    expect(updatePayload).toMatchObject({ version: 3, schema_version: 1 });
    expect(updatePayload).not.toHaveProperty("product_type");
    expect(activeRequested).toBe(false);
  });
});
