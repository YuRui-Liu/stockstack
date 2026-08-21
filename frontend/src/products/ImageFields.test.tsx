import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../test/fixtures";
import ImageFields from "./ImageFields";

describe("ImageFields", () => {
  it("预检主图并上传后组合 main 元数据", async () => {
    let uploadContentType = "";
    server.use(http.post("*/api/v1/uploads/images", ({ request }) => {
      uploadContentType = request.headers.get("content-type") ?? "";
      return HttpResponse.json({ url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }, { status: 201 });
    }));
    const values: unknown[] = [];
    render(<ImageFields value={[]} onChange={(value) => values.push(value)} />);
    fireEvent.change(screen.getByLabelText("主图"), { target: { files: [new File(["png"], "main.png", { type: "image/png" })] } });

    await waitFor(() => expect(values.at(-1)).toEqual([{ kind: "main", url: "/uploads/main.png", size_bytes: 12, mime_type: "image/png" }]));
    expect(uploadContentType).toContain("multipart/form-data");
  });

  it.each([
    [new File([new Uint8Array(2 * 1024 * 1024 + 1)], "large.png", { type: "image/png" }), "不能超过 2 MiB"],
    [new File(["bad"], "bad.gif", { type: "image/gif" }), "仅支持 JPEG、PNG 或 WebP"],
  ])("拒绝非法文件且保留错误", async (file, message) => {
    render(<ImageFields value={[]} onChange={() => undefined} />);
    fireEvent.change(screen.getByLabelText("主图"), { target: { files: [file] } });
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });
});
