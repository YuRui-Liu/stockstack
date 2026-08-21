import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { penalizedProduct, server } from "../test/fixtures";
import ProductListPage from "./ProductListPage";

const offShelfProduct = {
  ...penalizedProduct,
  id: "0198d72e-6700-7000-8000-000000000002",
  title: "春季外套",
  product_type: "creative" as const,
  price_amount: "128.50",
  stock: 7,
  status: "off_shelf" as const,
  version: 4,
  updated_at: "2026-08-21T10:30:00Z",
};

const onShelfProduct = {
  ...offShelfProduct,
  id: "0198d72e-6700-7000-8000-000000000003",
  title: "夏季外套",
  status: "on_shelf" as const,
  version: 2,
};

function LocationProbe() {
  const location = useLocation();
  return <output aria-label="当前地址">{location.search}</output>;
}

function renderPage(initialEntry = "/products") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/products" element={<><ProductListPage /><LocationProbe /></>} />
        <Route path="/products/:id/edit" element={<div>编辑页</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProductListPage", () => {
  it("从 URL 恢复组合筛选并在筛选或 page_size 变化时重置页码", async () => {
    const requests: URL[] = [];
    server.use(http.get("*/api/v1/products", ({ request }) => {
      requests.push(new URL(request.url));
      return HttpResponse.json({ items: [], total: 0, page: 3, page_size: 50 });
    }));

    renderPage("/products?query=%E5%A4%96%E5%A5%97&product_type=creative&status=off_shelf&page=3&page_size=50");
    await screen.findByText("暂无商品");
    expect(requests.at(-1)?.searchParams.get("query")).toBe("外套");
    expect(requests.at(-1)?.searchParams.get("product_type")).toBe("creative");
    expect(requests.at(-1)?.searchParams.get("status")).toBe("off_shelf");
    expect(requests.at(-1)?.searchParams.get("page")).toBe("3");
    expect(requests.at(-1)?.searchParams.get("page_size")).toBe("50");
    expect(screen.getByLabelText("商品关键词")).toHaveValue("外套");

    fireEvent.change(screen.getByLabelText("商品关键词"), { target: { value: "衬衫" } });
    fireEvent.click(screen.getByRole("button", { name: /查\s*询/ }));
    await waitFor(() => expect(screen.getByLabelText("当前地址")).toHaveTextContent("query=%E8%A1%AC%E8%A1%AB"));
    expect(screen.getByLabelText("当前地址")).toHaveTextContent("page=1");

    fireEvent.mouseDown(screen.getByRole("combobox", { name: "每页条数" }));
    fireEvent.click((await screen.findAllByText("20 条/页")).at(-1)!);
    await waitFor(() => expect(screen.getByLabelText("当前地址")).toHaveTextContent("page_size=20"));
    expect(screen.getByLabelText("当前地址")).toHaveTextContent("page=1");
  });

  it("显示商品关键信息、详情编辑入口和合法的单个状态操作", async () => {
    const updates: unknown[] = [];
    server.use(
      http.get("*/api/v1/products", () => HttpResponse.json({ items: [offShelfProduct, penalizedProduct], total: 2, page: 1, page_size: 20 })),
      http.patch("*/api/v1/products/:id/status", async ({ request }) => {
        updates.push(await request.json());
        return HttpResponse.json({ ...offShelfProduct, status: "on_shelf", version: 5 });
      }),
    );
    renderPage();

    const row = await screen.findByRole("row", { name: /春季外套/ });
    expect(within(row).getByRole("img", { name: "春季外套主图" })).toBeInTheDocument();
    expect(row).toHaveTextContent(offShelfProduct.id);
    expect(row).toHaveTextContent("创意商品");
    expect(row).toHaveTextContent("128.50");
    expect(row).toHaveTextContent("7");
    expect(row).toHaveTextContent("已下架");
    expect(within(row).getByRole("link", { name: "详情" })).toHaveAttribute("href", `/products/${offShelfProduct.id}`);
    expect(within(row).getByRole("link", { name: "编辑" })).toHaveAttribute("href", `/products/${offShelfProduct.id}/edit`);
    expect(screen.getByRole("row", { name: /处罚中的示例商品/ })).not.toHaveTextContent("恢复");

    fireEvent.click(within(row).getByRole("button", { name: "上架" }));
    await waitFor(() => expect(updates).toContainEqual({ target_status: "on_shelf", version: 4 }));
    expect(row).toHaveTextContent("已上架");
  });

  it("处罚操作要求二次确认", async () => {
    let update: unknown;
    server.use(
      http.get("*/api/v1/products", () => HttpResponse.json({ items: [onShelfProduct], total: 1, page: 1, page_size: 20 })),
      http.patch("*/api/v1/products/:id/status", async ({ request }) => {
        update = await request.json();
        return HttpResponse.json({ ...onShelfProduct, status: "penalized", version: 3 });
      }),
    );
    renderPage();
    const row = await screen.findByRole("row", { name: /夏季外套/ });
    fireEvent.click(within(row).getByRole("button", { name: "设为处罚" }));
    expect(await screen.findByText("确认将该商品设为处罚状态？")).toBeInTheDocument();
    expect(update).toBeUndefined();
    fireEvent.click(screen.getByRole("button", { name: "确认处罚" }));
    await waitFor(() => expect(update).toEqual({ target_status: "penalized", version: 2 }));
  });

  it("批量状态 409 时列出失败项、保留选择且不乐观修改行", async () => {
    const anotherOffShelfProduct = { ...onShelfProduct, status: "off_shelf" as const };
    server.use(
      http.get("*/api/v1/products", () => HttpResponse.json({ items: [offShelfProduct, anotherOffShelfProduct], total: 2, page: 1, page_size: 20 })),
      http.post("*/api/v1/products/batch-status", () => HttpResponse.json({
        code: "batch_status_conflict",
        message: "批量操作失败",
        field_errors: { [offShelfProduct.id]: ["版本冲突"], [onShelfProduct.id]: ["状态不允许"] },
        request_id: "batch-conflict",
      }, { status: 409 })),
    );
    renderPage();
    await screen.findByText("春季外套");
    const rows = screen.getAllByRole("row");
    fireEvent.click(within(rows[1]).getByRole("checkbox"));
    fireEvent.click(within(rows[2]).getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "批量上架" }));

    const dialog = await screen.findByRole("dialog", { name: "批量操作失败" });
    expect(dialog).toHaveTextContent(`${offShelfProduct.id}：版本冲突`);
    expect(dialog).toHaveTextContent(`${onShelfProduct.id}：状态不允许`);
    expect(within(rows[1]).getByRole("checkbox")).toBeChecked();
    expect(within(rows[2]).getByRole("checkbox")).toBeChecked();
    expect(rows[1]).toHaveTextContent("已下架");
    expect(rows[2]).toHaveTextContent("已下架");
    expect(screen.queryByRole("button", { name: "批量处罚" })).not.toBeInTheDocument();
  });

  it("批量提交前拒绝包含处罚商品的非法混选且不发送请求", async () => {
    let submitted = false;
    server.use(
      http.get("*/api/v1/products", () => HttpResponse.json({ items: [offShelfProduct, penalizedProduct], total: 2, page: 1, page_size: 20 })),
      http.post("*/api/v1/products/batch-status", () => {
        submitted = true;
        return HttpResponse.json([]);
      }),
    );
    renderPage();
    await screen.findByText("春季外套");
    const rows = screen.getAllByRole("row");
    fireEvent.click(within(rows[1]).getByRole("checkbox"));
    fireEvent.click(within(rows[2]).getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "批量上架" }));

    const dialog = await screen.findByRole("dialog", { name: "无法批量操作" });
    expect(dialog).toHaveTextContent(`${penalizedProduct.id}：处罚中 → 已上架`);
    expect(submitted).toBe(false);
  });
});
