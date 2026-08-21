import { Alert, Button, Card, Form, Input, InputNumber, Select, Space, Spin, Typography } from "antd";
import { useEffect, useRef, useState } from "react";

import { ApiError, createProduct, getActiveProductSchema, getProduct, getProductSchema, updateProduct } from "../api/client";
import type { FieldSchema, ProductCreate, ProductImageInput, ProductType, ProductView } from "../api/types";
import DynamicFields, { validateRenderableSchema } from "./DynamicFields";
import ImageFields from "./ImageFields";
import { fieldErrorsToForm, imageInputs, normalizeAttributes } from "./productForm";

interface FormValues extends Omit<ProductCreate, "schema_version"> { version?: number }

const typeOptions = [
  { value: "physical", label: "实物商品" }, { value: "virtual", label: "虚拟商品" }, { value: "creative", label: "创意商品" },
];
const noImages: ProductImageInput[] = [];

export default function ProductFormPage({ productId, initialImages = noImages }: { productId?: string; initialImages?: ProductImageInput[] }) {
  const [form] = Form.useForm();
  const [fieldSchema, setFieldSchema] = useState<FieldSchema>();
  const [product, setProduct] = useState<ProductView>();
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadsPending, setUploadsPending] = useState(false);
  const savingRef = useRef(false);
  const schemaRequest = useRef(0);

  useEffect(() => {
    let current = true;
    const load = async () => {
      setLoading(true); setError("");
      try {
        if (productId) {
          const detail = await getProduct(productId);
          const schema = await getProductSchema(detail.product_type, detail.schema_version);
          if (!current) return;
          setProduct(detail); setFieldSchema(schema);
          form.setFieldsValue({ ...detail, images: imageInputs(detail.images) });
        } else {
          const schema = await getActiveProductSchema("physical");
          if (!current) return;
          setFieldSchema(schema);
          form.setFieldsValue({ product_type: "physical", status: "off_shelf", delivery_method: "ems", return_rule: "seven_days", images: initialImages });
        }
      } catch (caught) { if (current) setError(caught instanceof ApiError ? caught.response.message : "商品表单加载失败"); }
      finally { if (current) { setLoading(false); setInitialized(true); } }
    };
    void load();
    return () => { current = false; };
  }, [form, initialImages, productId]);

  const changeType = async (type: ProductType) => {
    const request = ++schemaRequest.current;
    form.setFieldValue("attributes", {});
    setFieldSchema(undefined);
    setLoading(true); setError("");
    try {
      const schema = await getActiveProductSchema(type);
      if (request === schemaRequest.current) setFieldSchema(schema);
    }
    catch (caught) { if (request === schemaRequest.current) setError(caught instanceof ApiError ? caught.response.message : "字段配置加载失败"); }
    finally { if (request === schemaRequest.current) setLoading(false); }
  };

  const submit = async (values: FormValues) => {
    if (!fieldSchema || validateRenderableSchema(fieldSchema) || savingRef.current || uploadsPending) return;
    savingRef.current = true;
    setSaving(true);
    setError("");
    const base = { ...values, stock: Number(values.stock), price_amount: String(values.price_amount), attributes: normalizeAttributes(values.attributes), images: imageInputs(values.images), schema_version: fieldSchema.version };
    try {
      if (productId && product) {
        const { product_type: _productType, ...update } = base;
        await updateProduct(productId, { ...update, version: product.version });
      }
      else await createProduct(base);
    } catch (caught) {
      if (caught instanceof ApiError) {
        if (Object.keys(caught.response.field_errors).length) form.setFields(fieldErrorsToForm(caught.response.field_errors));
        if (caught.status === 409) setError(caught.response.code === "schema_version_conflict" ? "字段配置已更新，请重新载入页面后提交" : "商品已被其他人修改，请刷新页面后重试");
        else if (!Object.keys(caught.response.field_errors).length) setError(caught.response.message);
      } else setError("保存失败，请重试");
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const schemaError = fieldSchema ? validateRenderableSchema(fieldSchema) : null;

  if (!initialized) return <Spin aria-label="加载商品表单" />;
  return <Card style={{ maxWidth: 880, margin: "24px auto" }}>
    <Typography.Title level={2}>{productId ? "编辑商品" : "发布商品"}</Typography.Title>
    {error && <Alert role="alert" type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
    <Form form={form} layout="vertical" onFinish={(values) => void submit(values)} onFinishFailed={({ errorFields }) => setError(`请检查必填项：${errorFields.map((field) => field.name.join(".")).join("、")}`)} requiredMark={false}>
      <Form.Item name="product_type" label="商品类型" rules={[{ required: true }]}><Select disabled={!!productId} options={typeOptions} onChange={(value) => void changeType(value)} /></Form.Item>
      <Form.Item name="title" label="商品标题" rules={[{ required: true, message: "请输入商品标题" }]}><Input maxLength={60} /></Form.Item>
      <Form.Item name="short_title" label="短标题"><Input maxLength={120} /></Form.Item>
      <Space size="middle" style={{ display: "flex" }} align="start">
        <Form.Item name="price_amount" label="价格" rules={[
          { required: true, message: "请输入价格" },
          { pattern: /^(?:0|[1-9]\d*)(?:\.\d{1,2})?$/, message: "价格必须为非负数，且最多两位小数" },
        ]}><Input inputMode="decimal" /></Form.Item>
        <Form.Item name="stock" label="库存" rules={[{ required: true, message: "请输入库存" }]}><InputNumber min={0} precision={0} /></Form.Item>
      </Space>
      <Form.Item name="description_html" label="商品描述"><Input.TextArea rows={5} maxLength={2000} /></Form.Item>
      <Form.Item name="delivery_method" label="配送方式" rules={[{ required: true }]}><Select options={[{ value: "ems", label: "EMS" }, { value: "logistics", label: "物流" }, { value: "voucher", label: "电子凭证" }]} /></Form.Item>
      <Form.Item name="return_rule" label="退货规则" rules={[{ required: true }]}><Select options={[{ value: "seven_days", label: "七天无理由" }, { value: "no_returns", label: "不支持退货" }]} /></Form.Item>
      <Form.Item name="status" label="状态" rules={[{ required: true }]}><Select options={[{ value: "off_shelf", label: "下架" }, { value: "on_shelf", label: "上架" }, { value: "penalized", label: "处罚中" }]} /></Form.Item>
      {fieldSchema && <DynamicFields fieldSchema={fieldSchema} />}
      <Form.Item name="images" label="商品图片" rules={[{ validator: (_, value: ProductImageInput[] = []) => value.filter((image) => image.kind === "main").length === 1 ? Promise.resolve() : Promise.reject(new Error("请上传一张主图")) }]}><ImageFields onUploadingChange={setUploadsPending} /></Form.Item>
      <Button type="primary" htmlType="submit" loading={loading || saving || uploadsPending} disabled={!fieldSchema || !!schemaError || saving || uploadsPending}>{productId ? "保存修改" : "发布商品"}</Button>
    </Form>
  </Card>;
}
