import { render, screen } from "@testing-library/react";
import { Form } from "antd";
import { describe, expect, it } from "vitest";

import { creativeSchema, physicalSchema, virtualSchema } from "../test/fixtures";
import DynamicFields from "./DynamicFields";

describe("DynamicFields", () => {
  it.each([
    [physicalSchema, ["重量（千克）", "规格", "物流模板"], "核销方式"],
    [virtualSchema, ["有效期（天）", "核销方式", "兑换说明"], "重量（千克）"],
    [creativeSchema, ["素材类型", "投放尺寸", "文件地址"], "重量（千克）"],
  ] as const)("按 %s schema 生成安全控件", (fieldSchema, labels, absent) => {
    render(<Form><DynamicFields fieldSchema={fieldSchema} /></Form>);
    labels.forEach((label) => expect(screen.getByLabelText(label)).toBeInTheDocument());
    expect(screen.queryByLabelText(absent)).not.toBeInTheDocument();
  });

  it("遇到不支持的 schema 时阻断编辑", () => {
    render(<Form><DynamicFields fieldSchema={{ product_type: "physical", version: 2, schema: { type: "object", properties: { nested: { type: "object" } } } }} /></Form>);
    expect(screen.getByRole("alert")).toHaveTextContent("无法安全生成");
    expect(screen.queryByLabelText("nested")).not.toBeInTheDocument();
  });

  it("遇到无法安全编译的 pattern 时阻断而不崩溃", () => {
    render(<Form><DynamicFields fieldSchema={{ product_type: "physical", version: 2, schema: { type: "object", properties: { code: { type: "string", pattern: "[" } } } }} /></Form>);
    expect(screen.getByRole("alert")).toHaveTextContent("无法安全生成");
  });
});
