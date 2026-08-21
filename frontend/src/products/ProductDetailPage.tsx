import { Alert, Button, Card, Descriptions, Image, Space, Spin, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, getProduct } from "../api/client";
import type { ProductType, ProductView } from "../api/types";
import { statusLabels } from "./status";

const productTypeLabels: Record<ProductType, string> = {
  physical: "实物商品",
  virtual: "虚拟商品",
  creative: "创意商品",
};

export default function ProductDetailPage() {
  const { id = "" } = useParams();
  const [product, setProduct] = useState<ProductView>();
  const [error, setError] = useState("");

  useEffect(() => {
    let current = true;
    setError("");
    setProduct(undefined);
    void getProduct(id)
      .then((result) => { if (current) setProduct(result); })
      .catch((caught) => { if (current) setError(caught instanceof ApiError ? caught.response.message : "商品详情加载失败"); });
    return () => { current = false; };
  }, [id]);

  if (error) return <Alert role="alert" type="error" showIcon message={error} style={{ margin: 24 }} />;
  if (!product || product.id !== id) return <Spin aria-label="加载商品详情" style={{ margin: 24 }} />;

  return <main style={{ maxWidth: 1000, margin: "24px auto" }}>
    <Card>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
        <Typography.Title level={1} style={{ margin: 0 }}>{product.title}</Typography.Title>
        <Space>
          <Link to="/products"><Button>返回商品列表</Button></Link>
          <Link to={`/products/${product.id}/edit`}><Button type="primary">编辑商品</Button></Link>
        </Space>
      </Space>
      <Descriptions bordered column={2}>
        <Descriptions.Item label="商品 ID" span={2}>{product.id}</Descriptions.Item>
        <Descriptions.Item label="短标题">{product.short_title || "-"}</Descriptions.Item>
        <Descriptions.Item label="商品类型">{productTypeLabels[product.product_type]}</Descriptions.Item>
        <Descriptions.Item label="价格">{product.price_amount}</Descriptions.Item>
        <Descriptions.Item label="库存">{product.stock}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag>{statusLabels[product.status]}</Tag></Descriptions.Item>
        <Descriptions.Item label="版本">{product.version}</Descriptions.Item>
        <Descriptions.Item label="配送方式">{product.delivery_method}</Descriptions.Item>
        <Descriptions.Item label="退货规则">{product.return_rule}</Descriptions.Item>
        <Descriptions.Item label="字段配置版本" span={2}>{product.schema_version}</Descriptions.Item>
        <Descriptions.Item label="商品描述" span={2}>{product.description_html || "-"}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{new Date(product.created_at).toLocaleString("zh-CN", { hour12: false })}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{new Date(product.updated_at).toLocaleString("zh-CN", { hour12: false })}</Descriptions.Item>
        <Descriptions.Item label="动态属性" span={2}><pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(product.attributes, null, 2)}</pre></Descriptions.Item>
        <Descriptions.Item label="商品图片" span={2}>
          <Space wrap>{product.images.map((image, index) => <Image key={`${image.kind}-${image.sort_order}`} width={96} src={image.url} alt={`${product.title}${image.kind === "main" ? "主图" : `图片${index + 1}`}`} />)}</Space>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  </main>;
}
