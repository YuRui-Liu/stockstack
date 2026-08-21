import { fireEvent, render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { expect, it } from "vitest";

import { penalizedProduct, server } from "../test/fixtures";
import ProductDetailPage from "./ProductDetailPage";

it("按路由商品 ID 请求详情并显示公共字段、图片和动态属性", async () => {
  let requestedId = "";
  server.use(http.get("*/api/v1/products/:id", ({ params }) => {
    requestedId = String(params.id);
    return HttpResponse.json(penalizedProduct);
  }));

  render(
    <MemoryRouter initialEntries={[`/products/${penalizedProduct.id}`]}>
      <Routes><Route path="/products/:id" element={<ProductDetailPage />} /></Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: penalizedProduct.title })).toBeInTheDocument();
  expect(requestedId).toBe(penalizedProduct.id);
  expect(screen.getByText("99.00")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "处罚中的示例商品主图" })).toBeInTheDocument();
  expect(screen.getByText(/weight_kg/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "返回商品列表" })).toHaveAttribute("href", "/products");
  expect(screen.getByRole("link", { name: "编辑商品" })).toHaveAttribute("href", `/products/${penalizedProduct.id}/edit`);
  expect(screen.queryByRole("button", { name: /上架|下架|处罚/ })).not.toBeInTheDocument();
});

it("路由从 A 切到 B 时不显示 A 的详情和编辑入口", async () => {
  const productB = { ...penalizedProduct, id: "0198d72e-6700-7000-8000-000000000099", title: "商品 B" };
  let releaseB: (() => void) | undefined;
  const waitForB = new Promise<void>((resolve) => { releaseB = resolve; });
  server.use(http.get("*/api/v1/products/:id", async ({ params }) => {
    if (params.id === productB.id) await waitForB;
    return HttpResponse.json(params.id === productB.id ? productB : penalizedProduct);
  }));
  function NavigateToB() {
    const navigate = useNavigate();
    return <button onClick={() => navigate(`/products/${productB.id}`)}>打开 B</button>;
  }
  render(
    <MemoryRouter initialEntries={[`/products/${penalizedProduct.id}`]}>
      <NavigateToB />
      <Routes><Route path="/products/:id" element={<ProductDetailPage />} /></Routes>
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { name: penalizedProduct.title });
  fireEvent.click(screen.getByRole("button", { name: "打开 B" }));

  expect(screen.queryByRole("link", { name: "编辑商品" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("加载商品详情")).toBeInTheDocument();
  releaseB?.();
  expect(await screen.findByRole("heading", { name: "商品 B" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "编辑商品" })).toHaveAttribute("href", `/products/${productB.id}/edit`);
});
