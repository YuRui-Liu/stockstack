import { expect, type Page } from "@playwright/test";

const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", "base64");

const attributes = {
  physical: [["重量（千克）", "1.2"], ["规格", "标准盒装"]],
  virtual: [["有效期（天）", "30"], ["兑换说明", "输入兑换码"]],
  creative: [["投放尺寸", "1200x800"], ["文件地址", "https://assets.example/e2e.png"]],
} as const;

export async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("管理员账号").fill(process.env.E2E_ADMIN_USERNAME ?? "admin");
  await page.getByLabel("密码").fill(process.env.E2E_ADMIN_PASSWORD ?? "stockstack-demo");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("heading", { name: "商品管理" })).toBeVisible();
}

async function choose(page: Page, label: string, option: string) {
  await page.getByLabel(label, { exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

export async function publishProduct(page: Page, type: "physical" | "virtual" | "creative", title: string) {
  const labels = { physical: "实物商品", virtual: "虚拟商品", creative: "创意商品" };
  await page.goto("/products/new");
  await choose(page, "商品类型", labels[type]);
  await page.getByLabel("商品标题").fill(title);
  await page.getByLabel("短标题").fill(title);
  await page.getByLabel("价格").fill("19.90");
  await page.getByLabel("库存").fill("10");
  for (const [label, value] of attributes[type]) await page.getByLabel(label).fill(value);
  if (type === "physical") await choose(page, "物流模板", "standard");
  if (type === "virtual") await choose(page, "核销方式", "code");
  if (type === "creative") await choose(page, "素材类型", "image");
  await page.getByLabel("主图", { exact: true }).setInputFiles({ name: "main.png", mimeType: "image/png", buffer: png });
  const response = page.waitForResponse((candidate) => candidate.url().includes("/api/v1/products") && candidate.request().method() === "POST");
  await page.getByRole("button", { name: "发布商品", exact: true }).last().click();
  expect((await response).status()).toBe(201);
}

export function rowFor(page: Page, title: string) {
  return page.getByRole("row").filter({ has: page.getByRole("cell", { name: title, exact: true }) });
}
