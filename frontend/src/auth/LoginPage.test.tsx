import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "../app/App";

function renderApp(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <App />
    </MemoryRouter>,
  );
}

describe("管理员登录", () => {
  it("提交账号和密码后进入受保护的商品管理", async () => {
    renderApp("/login");

    fireEvent.change(screen.getByLabelText("管理员账号"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: /登\s*录/ }));

    expect(await screen.findByRole("heading", { name: "商品管理" })).toBeInTheDocument();
    expect(sessionStorage.getItem("stockstack_access_token")).toBe("test-access-token");
  });

  it("未登录访问受保护路由时重定向到登录", async () => {
    renderApp("/products");

    expect(await screen.findByRole("heading", { name: "管理员登录" })).toBeInTheDocument();
    expect(screen.getByLabelText("管理员账号")).toHaveFocus();
  });
});
