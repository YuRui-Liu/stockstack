import { Alert, DatePicker, Form, Input, InputNumber, Select } from "antd";
import dayjs from "dayjs";
import type { ReactNode } from "react";

import type { FieldSchema, JSONSchemaProperty } from "../api/types";

const fallbackLabels: Record<string, string> = {
  weight_kg: "重量（千克）", specification: "规格", shipping_template: "物流模板",
  validity_days: "有效期（天）", verification_method: "核销方式", redemption_instructions: "兑换说明",
  asset_type: "素材类型", dimensions: "投放尺寸", file_url: "文件地址",
};

function fieldControl(key: string, property: JSONSchemaProperty): ReactNode | undefined {
  if (Array.isArray(property.enum) && property.enum.every((item) => ["string", "number"].includes(typeof item))) {
    return <Select options={property.enum.map((value) => ({ label: String(value), value }))} />;
  }
  if (property.type === "number" || property.type === "integer") {
    return <InputNumber min={property.minimum} max={property.maximum} step={property.type === "integer" ? 1 : undefined} style={{ width: "100%" }} />;
  }
  if (property.type === "string" && property.format === "date") return <DatePicker style={{ width: "100%" }} />;
  if (property.type === "string" && (property.maxLength && property.maxLength >= 200 || /description|instructions/i.test(key))) {
    return <Input.TextArea maxLength={property.maxLength} rows={4} />;
  }
  if (property.type === "string") return <Input maxLength={property.maxLength} />;
  return undefined;
}

export default function DynamicFields({ fieldSchema }: { fieldSchema: FieldSchema }) {
  const schema = fieldSchema.schema;
  if (schema.type !== "object" || !schema.properties || typeof schema.properties !== "object") {
    return <Alert type="error" showIcon message="无法安全生成商品字段，请联系管理员" />;
  }
  const generated = Object.entries(schema.properties).map(([key, property]) => {
    let pattern: RegExp | undefined;
    try { pattern = property.pattern ? new RegExp(property.pattern) : undefined; }
    catch { return { key, property, control: undefined, pattern: undefined }; }
    return { key, property, control: fieldControl(key, property), pattern };
  });
  if (generated.some(({ control }) => !control)) {
    return <Alert type="error" showIcon message="无法安全生成部分商品字段，请联系管理员" />;
  }
  const required = new Set(schema.required ?? []);
  return <>
    {generated.map(({ key, property, control, pattern }) => (
      <Form.Item
        key={key}
        name={["attributes", key]}
        label={property.title || fallbackLabels[key] || key}
        rules={[
          { required: required.has(key), message: `请输入${property.title || fallbackLabels[key] || key}` },
          ...(pattern ? [{ pattern, message: "格式不正确" }] : []),
        ]}
        {...(property.type === "string" && property.format === "date" ? {
          getValueProps: (value: unknown) => ({ value: typeof value === "string" ? dayjs(value) : value }),
        } : {})}
      >{control}</Form.Item>
    ))}
  </>;
}
