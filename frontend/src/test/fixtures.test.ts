import { describe, expect, it } from "vitest";

import { creativeSchema, physicalSchema } from "./fixtures";

describe("商品字段模板夹具契约", () => {
  it("保持后端规定的规格长度与文件地址格式", () => {
    const specification = physicalSchema.schema.properties.specification;
    const fileUrl = creativeSchema.schema.properties.file_url;

    expect(specification).toMatchObject({ maxLength: 100 });
    expect(fileUrl).toMatchObject({ format: "http-url" });
  });
});
