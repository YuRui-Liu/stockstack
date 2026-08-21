import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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
