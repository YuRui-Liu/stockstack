import { expect, test } from "@playwright/test";

import { login, publishProduct, rowFor } from "./helpers";

test.describe.configure({ mode: "serial" });

test("管理员完成商品发布、筛选、编辑和状态治理核心旅程", async ({ page }) => {
  const suffix = Date.now();
  const physical = `E2E 实物 ${suffix}`;
  const virtual = `E2E 虚拟 ${suffix}`;
  const creative = `E2E 创意 ${suffix}`;

  await login(page);
  await publishProduct(page, "physical", physical);
  await publishProduct(page, "virtual", virtual);
  await publishProduct(page, "creative", creative);

  await page.goto("/products");
  await page.getByLabel("商品关键词").fill(`E2E`);
  await page.getByLabel("商品类型").click();
  await page.getByRole("option", { name: "实物商品", exact: true }).click();
  await page.getByLabel("商品状态").click();
  await page.getByRole("option", { name: "已下架", exact: true }).click();
  await page.getByRole("button", { name: "查询", exact: true }).click();
  await expect(rowFor(page, physical)).toBeVisible();
  await expect(rowFor(page, virtual)).toHaveCount(0);

  await rowFor(page, physical).getByRole("link", { name: "编辑" }).click();
  await page.getByLabel("短标题").fill("E2E 已编辑");
  const editResponse = page.waitForResponse((candidate) => candidate.request().method() === "PUT");
  await page.getByRole("button", { name: "保存修改" }).click();
  expect((await editResponse).status()).toBe(200);

  await page.goto(`/products?query=${encodeURIComponent(`E2E`)}&status=off_shelf&page=1&page_size=20`);
  await rowFor(page, physical).getByRole("button", { name: "上架", exact: true }).click();
  await expect(rowFor(page, physical).getByText("已上架", { exact: true })).toBeVisible();
  await rowFor(page, physical).getByRole("button", { name: "下架", exact: true }).click();
  await expect(rowFor(page, physical).getByText("已下架", { exact: true })).toBeVisible();

  for (const title of [physical, virtual]) await rowFor(page, title).getByRole("checkbox").check();
  await page.getByRole("button", { name: "批量上架", exact: true }).click();
  await expect(rowFor(page, physical).getByText("已上架", { exact: true })).toBeVisible();
  await expect(rowFor(page, virtual).getByText("已上架", { exact: true })).toBeVisible();

  for (const title of [physical, virtual]) await rowFor(page, title).getByRole("checkbox").check();
  await page.getByRole("button", { name: "批量下架", exact: true }).click();
  await expect(rowFor(page, physical).getByText("已下架", { exact: true })).toBeVisible();

  await rowFor(page, creative).getByRole("button", { name: "设为处罚", exact: true }).click();
  await page.getByRole("button", { name: "确认处罚", exact: true }).click();
  await expect(rowFor(page, creative).getByText("处罚中", { exact: true })).toBeVisible();
  await expect(rowFor(page, creative).getByRole("button", { name: /上架|下架/ })).toHaveCount(0);
});
