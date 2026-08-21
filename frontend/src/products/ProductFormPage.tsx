import { Alert, Button, Form, Input, InputNumber, Radio, Select, Spin } from "antd";
import { useEffect, useRef, useState } from "react";
import { useInRouterContext, Link } from "react-router-dom";

import { ApiError, createProduct, getActiveProductSchema, getProduct, getProductSchema, updateProduct } from "../api/client";
import type { FieldSchema, ProductCreate, ProductImageInput, ProductType, ProductView } from "../api/types";
import DynamicFields, { validateRenderableSchema } from "./DynamicFields";
import ImageFields from "./ImageFields";
import { fieldErrorsToForm, imageInputs, normalizeAttributes } from "./productForm";

interface FormValues extends Omit<ProductCreate, "schema_version"> { version?: number }

const typeOptions = [
  { value: "physical", label: "实物商品" }, { value: "virtual", label: "虚拟商品" }, { value: "creative", label: "创意商品" },
];
const deliveryOptions = [
  { value: "ems", label: "EMS" }, { value: "logistics", label: "物流" }, { value: "voucher", label: "电子凭证" },
];
const returnOptions = [
  { value: "seven_days", label: "七天无理由" }, { value: "no_returns", label: "不支持退货" },
];
const statusOptions = [
  { value: "off_shelf", label: "下架" }, { value: "on_shelf", label: "上架" }, { value: "penalized", label: "处罚中" },
];
const noImages: ProductImageInput[] = [];

function SectionTitle({ title, required }: { title: string; required?: boolean }) {
  return <h2 className="ss-section-title">
    {required && <span className="ss-section-required">*</span>}
    {title}
  </h2>;
}

/** 表单页在单元测试中会脱离 Router 渲染，这里保证导航入口在两种环境下都可用 */
function NavAction({ to, children }: { to: string; children: React.ReactNode }) {
  const inRouter = useInRouterContext();
  return inRouter ? <Link to={to}>{children}</Link> : <a href={to}>{children}</a>;
}

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
  const submitDisabled = !fieldSchema || !!schemaError || saving || uploadsPending;

  if (!initialized) return <Spin aria-label="加载商品表单" style={{ margin: 24 }} />;

  return <div className="ss-form-page">
    <div className="ss-form-header">
      <NavAction to="/products"><Button type="link" className="ss-back-btn">返回列表</Button></NavAction>
      <h1 className="ss-page-title">{productId ? "编辑商品" : "发布商品"}</h1>
    </div>

    <Form
      form={form}
      layout="vertical"
      onFinish={(values) => void submit(values)}
      onFinishFailed={({ errorFields }) => setError(`请检查必填项：${errorFields.map((field) => field.name.join(".")).join("、")}`)}
    >
      <div className="ss-form-layout">
        <div className="ss-form-main">
          {error && <Alert role="alert" type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
          <div className="ss-form-stack">
            <section className="ss-form-section">
              <SectionTitle title="基本信息" required />
              <div className="ss-section-body">
                <Form.Item name="product_type" label="商品类型" tooltip="商品类型决定动态字段模板，创建后不可修改" rules={[{ required: true }]}>
                  <Select disabled={!!productId} options={typeOptions} onChange={(value) => void changeType(value)} />
                </Form.Item>
                <Form.Item name="title" label="商品标题" tooltip="标题展示在列表和详情页，建议包含品牌、品类与核心卖点" rules={[{ required: true, message: "请输入商品标题" }]}>
                  <Input maxLength={60} showCount placeholder="请输入商品标题，不超过 60 个字" />
                </Form.Item>
                <Form.Item name="short_title" label="短标题" tooltip="用于列表页短展示，不超过 120 个字">
                  <Input maxLength={120} showCount placeholder="请输入商品短标题，不超过 120 个字" />
                </Form.Item>
                <div className="ss-form-row" style={{ marginBottom: 20 }}>
                  <Form.Item name="price_amount" label="价格" rules={[
                    { required: true, message: "请输入价格" },
                    { pattern: /^(?:0|[1-9]\d*)(?:\.\d{1,2})?$/, message: "价格必须为非负数，且最多两位小数" },
                  ]}><Input inputMode="decimal" placeholder="0.00" /></Form.Item>
                  <Form.Item name="stock" label="库存" rules={[{ required: true, message: "请输入库存" }]}>
                    <InputNumber min={0} precision={0} style={{ width: "100%" }} placeholder="请输入库存数量" />
                  </Form.Item>
                </div>
                <Form.Item name="description_html" label="商品描述" tooltip="支持富文本内容，服务端会做安全清理，不超过 2000 字" style={{ marginBottom: 0 }}>
                  <Input.TextArea rows={5} maxLength={2000} showCount placeholder="请输入商品详情描述，支持图文内容，不超过 2000 字" />
                </Form.Item>
              </div>
            </section>

            {fieldSchema && (
              <section className="ss-form-section">
                <SectionTitle title={`${typeOptions.find((option) => option.value === (product?.product_type ?? form.getFieldValue("product_type")))?.label ?? "商品"}专属字段`} />
                <div className="ss-section-body">
                  <DynamicFields fieldSchema={fieldSchema} />
                  <span className="ss-upload-hint">字段模板版本 v{fieldSchema.version}，由后端按商品类型下发</span>
                </div>
              </section>
            )}

            <section className="ss-form-section">
              <SectionTitle title="图文信息" required />
              <div className="ss-section-body">
                <Form.Item
                  name="images"
                  label="商品图片"
                  required
                  style={{ marginBottom: 0 }}
                  rules={[{ validator: (_, value: ProductImageInput[] = []) => value.filter((image) => image.kind === "main").length === 1 ? Promise.resolve() : Promise.reject(new Error("请上传一张主图")) }]}
                >
                  <ImageFields onUploadingChange={setUploadsPending} />
                </Form.Item>
              </div>
            </section>

            <section className="ss-form-section">
              <SectionTitle title="服务与售后" required />
              <div className="ss-section-body">
                <Form.Item name="delivery_method" label="配送方式" rules={[{ required: true, message: "请选择配送方式" }]}>
                  <Radio.Group options={deliveryOptions} optionType="button" buttonStyle="solid" />
                </Form.Item>
                <Form.Item name="return_rule" label="退货规则" rules={[{ required: true, message: "请选择退货规则" }]}>
                  <Radio.Group options={returnOptions} optionType="button" buttonStyle="solid" />
                </Form.Item>
                <Form.Item
                  name="status"
                  label="状态"
                  tooltip="上架后商品对外可见；下架后公开接口视为不存在；处罚为终态"
                  rules={[{ required: true }]}
                  extra={productId ? "状态请在商品管理列表中操作" : undefined}
                  style={{ marginBottom: 0 }}
                >
                  <Select disabled={!!productId} options={statusOptions} />
                </Form.Item>
              </div>
            </section>
          </div>
        </div>

        <aside className="ss-form-sidebar">
          <div className="ss-sidebar-card">
            <h3 className="ss-sidebar-title">发布须知</h3>
            <ul className="ss-sidebar-list">
              <li>商品标题不能超过 60 个字，建议包含核心卖点</li>
              <li>主图必须上传，建议使用 800x800px 的正方形图片</li>
              <li>副图最多上传 5 张，每张不超过 2 MiB</li>
              <li>价格和库存为必填项，请如实填写</li>
              <li>专属字段随商品类型变化，切换类型会重置已填内容</li>
              <li>处罚状态为终态，设置后无法再切换上下架</li>
            </ul>
          </div>
        </aside>
      </div>

      <div className="ss-form-footer">
        <div className="ss-footer-inner">
          <NavAction to="/products"><Button size="large">取消</Button></NavAction>
          <Button
            type="primary"
            size="large"
            htmlType="submit"
            loading={loading || saving || uploadsPending}
            disabled={submitDisabled}
          >{productId ? "保存修改" : "发布商品"}</Button>
        </div>
      </div>
    </Form>
  </div>;
}
