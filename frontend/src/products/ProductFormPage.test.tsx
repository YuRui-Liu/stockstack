import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { message } from "antd";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { creativeSchema, penalizedProduct, physicalSchema, server, virtualSchema } from "../test/fixtures";
import ProductFormPage from "./ProductFormPage";

function fillCommonFields() {
  fireEvent.change(screen.getByLabelText("商品标题"), { target: { value: "新商品" } });
  fireEvent.change(screen.getByLabelText("短标题"), { target: { value: "新品" } });
  fireEvent.change(screen.getByLabelText("价格"), { target: { value: "19.90" } });
  fireEvent.change(screen.getByLabelText("库存"), { target: { value: "5" } });
  fireEvent.change(screen.getByLabelText("商品描述"), { target: { value: "描述" } });
}

async function fillPhysicalFields() {
  fillCommonFields();
  fireEvent.change(screen.getByLabelText("重量（千克）"), { target: { value: "1" } });
  fireEvent.change(screen.getByLabelText("规格"), { target: { value: "标准" } });
  fireEvent.mouseDown(screen.getByLabelText("物流模板"));
  fireEvent.click((await screen.findAllByText("standard")).at(-1)!);
}

describe("ProductFormPage", () => {
  it("创建时切换类型读取 active schema 并提交完整契约", async () => {
    let submitted: Record<string, unknown> | undefined;
    const onSaved = vi.fn();
    server.use(
      http.get("*/api/v1/product-schemas/:type/active", ({ params }) => HttpResponse.json(params.type === "virtual" ? virtualSchema : physicalSchema)),
      http.post("*/api/v1/products", async ({ request }) => {
        submitted = await request.json() as Record<string, unknown>;
        return HttpResponse.json({ ...penalizedProduct, ...submitted, id: "created", version: 1 }, { status: 201 });
      }),
    );
    render(<ProductFormPage onSaved={onSaved} initialImages={[{ kind: "main", url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }]} />);
    await screen.findByLabelText("重量（千克）");
    expect(screen.getByLabelText("状态")).not.toBeDisabled();
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
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ id: "created" }));
  });

  it("编辑成功后显示提示并通知页面跳转", async () => {
    const onSaved = vi.fn();
    const successMessage = vi.spyOn(message, "success");
    server.use(
      http.get("*/api/v1/products/:id", () => HttpResponse.json(penalizedProduct)),
      http.get("*/api/v1/product-schemas/physical/1", () => HttpResponse.json(physicalSchema)),
      http.put("*/api/v1/products/:id", () => HttpResponse.json({ ...penalizedProduct, title: "已更新商品", version: 4 })),
    );

    render(<ProductFormPage productId={penalizedProduct.id} onSaved={onSaved} />);
    await screen.findByRole("button", { name: "保存修改" });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ title: "已更新商品", version: 4 })));
    expect(successMessage).toHaveBeenCalledWith("商品修改成功");
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

  it("切换类型加载 active schema 失败后清空旧字段并阻断提交", async () => {
    server.use(http.get("*/api/v1/product-schemas/:type/active", ({ params }) => {
      if (params.type === "virtual") {
        return HttpResponse.json({ code: "schema_unavailable", message: "字段配置加载失败", field_errors: {}, request_id: "schema-failed" }, { status: 503 });
      }
      return HttpResponse.json(physicalSchema);
    }));
    render(<ProductFormPage initialImages={[]} />);
    await screen.findByLabelText("重量（千克）");
    fireEvent.mouseDown(screen.getByLabelText("商品类型"));
    fireEvent.click((await screen.findAllByText("虚拟商品")).at(-1)!);

    expect(await screen.findByRole("alert")).toHaveTextContent("字段配置加载失败");
    expect(screen.queryByLabelText("重量（千克）")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /发布商品/ })).toBeDisabled();
  });

  it("拒绝负价格并且不发送创建请求", async () => {
    let submitted = false;
    server.use(
      http.get("*/api/v1/product-schemas/physical/active", () => HttpResponse.json(physicalSchema)),
      http.post("*/api/v1/products", () => { submitted = true; return HttpResponse.json(penalizedProduct, { status: 201 }); }),
    );
    render(<ProductFormPage initialImages={[{ kind: "main", url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }]} />);
    await screen.findByLabelText("重量（千克）");
    fillCommonFields();
    fireEvent.change(screen.getByLabelText("价格"), { target: { value: "-1" } });
    fireEvent.click(screen.getByRole("button", { name: "发布商品" }));
    expect(await screen.findByText("价格必须为非负数，且最多两位小数")).toBeInTheDocument();
    expect(submitted).toBe(false);
  });

  it("无主图时不能提交", async () => {
    let submitted = false;
    server.use(
      http.get("*/api/v1/product-schemas/physical/active", () => HttpResponse.json(physicalSchema)),
      http.post("*/api/v1/products", () => { submitted = true; return HttpResponse.json(penalizedProduct, { status: 201 }); }),
    );
    render(<ProductFormPage initialImages={[]} />);
    await screen.findByLabelText("重量（千克）");
    fillCommonFields();
    fireEvent.click(screen.getByRole("button", { name: "发布商品" }));
    expect(await screen.findByText("请上传一张主图")).toBeInTheDocument();
    expect(submitted).toBe(false);
  });

  it("保存请求进行中时同步阻止重复提交", async () => {
    let posts = 0;
    let release: (() => void) | undefined;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    server.use(
      http.get("*/api/v1/product-schemas/physical/active", () => HttpResponse.json(physicalSchema)),
      http.post("*/api/v1/products", async () => { posts += 1; await pending; return HttpResponse.json(penalizedProduct, { status: 201 }); }),
    );
    render(<ProductFormPage initialImages={[{ kind: "main", url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }]} />);
    await screen.findByLabelText("重量（千克）");
    await fillPhysicalFields();
    const form = screen.getByRole("button", { name: "发布商品" }).closest("form")!;
    fireEvent.submit(form); fireEvent.submit(form);
    await waitFor(() => expect(posts).toBe(1));
    expect(screen.getByRole("button", { name: /发布商品/ })).toBeDisabled();
    release?.();
  });

  it("不可渲染 schema 阻断提交", async () => {
    let posts = 0;
    server.use(
      http.get("*/api/v1/product-schemas/physical/active", () => HttpResponse.json({ ...physicalSchema, schema: { type: "object", properties: { broken: null } } })),
      http.post("*/api/v1/products", () => { posts += 1; return HttpResponse.json(penalizedProduct); }),
    );
    render(<ProductFormPage initialImages={[]} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("无法安全生成");
    expect(screen.getByRole("button", { name: "发布商品" })).toBeDisabled();
    expect(posts).toBe(0);
  });

  it("图片上传期间阻断提交，完成后恢复", async () => {
    let posts = 0;
    let release: (() => void) | undefined;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    server.use(
      http.get("*/api/v1/product-schemas/physical/active", () => HttpResponse.json(physicalSchema)),
      http.post("*/api/v1/uploads/images", async () => { await pending; return HttpResponse.json({ url: "/uploads/main.png", size_bytes: 3, mime_type: "image/png" }, { status: 201 }); }),
      http.post("*/api/v1/products", () => { posts += 1; return HttpResponse.json(penalizedProduct, { status: 201 }); }),
    );
    render(<ProductFormPage initialImages={[]} />);
    await screen.findByLabelText("重量（千克）");
    await fillPhysicalFields();
    fireEvent.change(screen.getByLabelText("主图"), { target: { files: [new File(["png"], "main.png", { type: "image/png" })] } });
    const button = screen.getByRole("button", { name: /发布商品/ });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(posts).toBe(0);
    release?.();
    await waitFor(() => expect(button).not.toBeDisabled());
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

  it("编辑时禁用状态并保留原状态提交", async () => {
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
    expect(screen.getByLabelText("状态")).toBeDisabled();
    expect(screen.getByText("状态请在商品管理列表中操作")).toBeInTheDocument();
    expect(screen.getByLabelText("重量（千克）")).toHaveValue("0.5");
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("刷新");
    expect(updatePayload).toMatchObject({ version: 3, schema_version: 1, status: "penalized" });
    expect(updatePayload).not.toHaveProperty("product_type");
    expect(activeRequested).toBe(false);
  });
});
