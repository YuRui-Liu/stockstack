import { Alert, Button, Card, Form, Image, Input, Modal, Select, Space, Table, Tag, Typography } from "antd";
import type { TablePaginationConfig } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ApiError, batchUpdateProductStatus, listProducts, updateProductStatus } from "../api/client";
import type { ProductListParams, ProductStatus, ProductType, ProductView } from "../api/types";
import { actionsForStatus, batchStatusActions, canTransition, statusLabels, type StatusAction } from "./status";

const productTypeLabels: Record<ProductType, string> = {
  physical: "实物商品",
  virtual: "虚拟商品",
  creative: "创意商品",
};

const actionTextStyle = { fontSize: 14, fontWeight: 400 } as const;

function positiveInteger(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function paramsFromSearch(search: URLSearchParams): ProductListParams {
  const productType = search.get("product_type");
  const status = search.get("status");
  return {
    query: search.get("query") || undefined,
    product_type: productType === "physical" || productType === "virtual" || productType === "creative" ? productType : undefined,
    status: status === "on_shelf" || status === "off_shelf" || status === "penalized" ? status : undefined,
    page: positiveInteger(search.get("page"), 1),
    page_size: Math.min(100, positiveInteger(search.get("page_size"), 20)),
  };
}

function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return "商品操作失败，请重试";
  const failures = Object.entries(error.response.field_errors).flatMap(([id, reasons]) => reasons.map((reason) => `${id}：${reason}`));
  return failures.length ? failures.join("；") : error.response.message;
}

export default function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => paramsFromSearch(searchParams), [searchParams]);
  const [form] = Form.useForm();
  const [products, setProducts] = useState<ProductView[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedIds, setSelectedIds] = useState<React.Key[]>([]);
  const [confirming, setConfirming] = useState<{ product: ProductView; action: StatusAction }>();
  const [batchDialog, setBatchDialog] = useState<{ title: string; lines: string[] }>();
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const pendingIdsRef = useRef(new Set<string>());
  const [batchPending, setBatchPending] = useState(false);
  const [refreshGeneration, setRefreshGeneration] = useState(0);
  const batchPendingRef = useRef(false);
  const queryGeneration = useRef(0);

  useEffect(() => {
    form.setFieldsValue({ query: params.query, product_type: params.product_type, status: params.status });
  }, [form, params.product_type, params.query, params.status]);

  useEffect(() => {
    let current = true;
    queryGeneration.current += 1;
    setLoading(true);
    setError("");
    setProducts([]);
    setTotal(0);
    setSelectedIds([]);
    void listProducts(params)
      .then((page) => {
        if (!current) return;
        setProducts(page.items);
        setTotal(page.total);
      })
      .catch((caught) => { if (current) setError(errorText(caught)); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [params, refreshGeneration]);

  const writeParams = (next: ProductListParams) => {
    queryGeneration.current += 1;
    setSelectedIds([]);
    setProducts([]);
    setTotal(0);
    const search = new URLSearchParams();
    if (next.query) search.set("query", next.query);
    if (next.product_type) search.set("product_type", next.product_type);
    if (next.status) search.set("status", next.status);
    search.set("page", String(next.page));
    search.set("page_size", String(next.page_size));
    if (search.toString() === searchParams.toString()) setRefreshGeneration((current) => current + 1);
    else setSearchParams(search);
  };

  const changeStatus = async (product: ProductView, target: ProductStatus) => {
    if (pendingIdsRef.current.has(product.id)) return;
    pendingIdsRef.current.add(product.id);
    setPendingIds(new Set(pendingIdsRef.current));
    const generation = queryGeneration.current;
    setError("");
    try {
      const updated = await updateProductStatus(product.id, { target_status: target, version: product.version });
      if (generation === queryGeneration.current) setProducts((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (caught) {
      if (generation === queryGeneration.current) setError(errorText(caught));
    } finally {
      pendingIdsRef.current.delete(product.id);
      setPendingIds(new Set(pendingIdsRef.current));
    }
  };

  const runAction = (product: ProductView, action: StatusAction) => {
    if (action.requiresConfirmation) setConfirming({ product, action });
    else void changeStatus(product, action.target);
  };

  const batchChange = async (target: "on_shelf" | "off_shelf") => {
    if (batchPendingRef.current) return;
    setError("");
    const selected = products.filter((product) => selectedIds.includes(product.id));
    if (!selected.length) return;
    const invalid = selected.filter((product) => !canTransition(product.status, target));
    if (invalid.length) {
      setBatchDialog({
        title: "无法批量操作",
        lines: invalid.map((product) => `${product.id}：${statusLabels[product.status]} → ${statusLabels[target]}`),
      });
      return;
    }
    batchPendingRef.current = true;
    setBatchPending(true);
    const generation = queryGeneration.current;
    try {
      const updated = await batchUpdateProductStatus({
        product_ids: selected.map((product) => ({ product_id: product.id, version: product.version })),
        target_status: target,
      });
      const replacements = new Map(updated.map((product) => [product.id, product]));
      if (generation === queryGeneration.current) {
        setProducts((current) => current.map((product) => replacements.get(product.id) ?? product));
        setSelectedIds([]);
      }
    } catch (caught) {
      if (generation !== queryGeneration.current) return;
      if (caught instanceof ApiError && caught.status === 409) {
        const lines = Object.entries(caught.response.field_errors).flatMap(([id, reasons]) => reasons.map((reason) => `${id}：${reason}`));
        setBatchDialog({ title: "批量操作失败", lines: lines.length ? lines : [caught.response.message] });
      } else setError(errorText(caught));
    } finally {
      batchPendingRef.current = false;
      setBatchPending(false);
    }
  };

  const columns = [
    { title: "主图", key: "image", width: 80, render: (_: unknown, product: ProductView) => {
      const main = product.images.find((image) => image.kind === "main");
      return main ? <Image className="product-image" width={48} height={48} src={main.url} alt={`${product.title}主图`} preview={false} /> : "无主图";
    } },
    { title: "商品 ID", dataIndex: "id", key: "id", render: (value: string) => <Typography.Text className="product-id" title={value}>{value}</Typography.Text> },
    { title: "标题", dataIndex: "title", key: "title", render: (value: string) => <Typography.Text className="product-title">{value}</Typography.Text> },
    { title: "类型", dataIndex: "product_type", key: "product_type", render: (value: ProductType) => productTypeLabels[value] },
    { title: "价格", dataIndex: "price_amount", key: "price_amount", render: (value: string) => value },
    { title: "库存", dataIndex: "stock", key: "stock" },
    { title: "状态", dataIndex: "status", key: "status", render: (value: ProductStatus) => <Tag className={`status-tag status-tag--${value}`}>{statusLabels[value]}</Tag> },
    { title: "更新时间", dataIndex: "updated_at", key: "updated_at", render: (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false }) },
    { title: "操作", key: "actions", fixed: "right" as const, width: 280, render: (_: unknown, product: ProductView) => <div className="product-actions">
      <Link style={actionTextStyle} to={`/products/${product.id}`}>详情</Link>
      <Link style={actionTextStyle} to={`/products/${product.id}/edit`}>编辑</Link>
      {actionsForStatus(product.status).map((action) => <Button style={actionTextStyle} key={action.target} type="link" disabled={pendingIds.has(product.id)} loading={pendingIds.has(product.id)} onClick={() => runAction(product, action)}>{action.label}</Button>)}
    </div> },
  ];

  const changeTable = (pagination: TablePaginationConfig) => {
    writeParams({ ...params, page: pagination.pageSize === params.page_size ? pagination.current ?? 1 : 1, page_size: pagination.pageSize ?? 20 });
  };

  return <main className="page-container">
    <header className="page-heading"><Typography.Title className="page-title" level={1}>商品管理</Typography.Title><Typography.Text className="page-subtitle">统一管理商品信息、库存及上下架状态</Typography.Text></header>
    <Card className="surface-card">
      <Form className="filter-form" form={form} layout="inline" onFinish={(values) => writeParams({ ...params, ...values, query: values.query?.trim() || undefined, page: 1 })}>
        <Form.Item name="query" label="商品关键词"><Input className="filter-keyword" allowClear placeholder="请输入商品标题或 ID" /></Form.Item>
        <Form.Item name="product_type" label="商品类型"><Select allowClear style={{ width: 140 }} options={Object.entries(productTypeLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
        <Form.Item name="status" label="商品状态"><Select allowClear style={{ width: 120 }} options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
        <Button type="primary" htmlType="submit">查询</Button>
      </Form>
      {error && <Alert role="alert" type="error" showIcon message={error} style={{ marginTop: 16 }} />}
      <div className="table-toolbar"><Space>{batchStatusActions.map((action) => <Button key={action.target} disabled={!selectedIds.length || batchPending} loading={batchPending} onClick={() => void batchChange(action.target)}>{action.label}</Button>)}<Typography.Text className="selection-hint">{selectedIds.length ? `已选择 ${selectedIds.length} 项` : "选择商品后可批量操作"}</Typography.Text></Space><Select aria-label="每页条数" value={params.page_size} style={{ width: 120 }} onChange={(pageSize) => writeParams({ ...params, page: 1, page_size: pageSize })} options={[10, 20, 50, 100].map((value) => ({ value, label: `${value} 条/页` }))} /></div>
      <Table<ProductView>
        className="product-table"
        rowKey="id"
        loading={loading}
        locale={{ emptyText: loading ? "加载中" : "暂无商品" }}
        dataSource={products}
        columns={columns}
        scroll={{ x: 1500 }}
        rowSelection={{ selectedRowKeys: selectedIds, onChange: setSelectedIds }}
        pagination={{ current: params.page, pageSize: params.page_size, total, showSizeChanger: false }}
        onChange={changeTable}
      />
    </Card>
    <Modal
      open={!!confirming}
      getContainer={false}
      title="确认处罚"
      okText="确认处罚"
      cancelText="取消"
      onCancel={() => setConfirming(undefined)}
      onOk={() => {
        if (confirming) void changeStatus(confirming.product, confirming.action.target);
        setConfirming(undefined);
      }}
    >确认将该商品设为处罚状态？</Modal>
    <Modal
      open={!!batchDialog}
      title={batchDialog?.title}
      footer={<Button type="primary" onClick={() => setBatchDialog(undefined)}>知道了</Button>}
      onCancel={() => setBatchDialog(undefined)}
      getContainer={false}
    >
      <ul>{batchDialog?.lines.map((line) => <li key={line}>{line}</li>)}</ul>
    </Modal>
  </main>;
}
