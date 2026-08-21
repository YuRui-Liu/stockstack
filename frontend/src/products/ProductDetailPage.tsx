import { Alert, Button, Image, Spin } from "antd";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, getProduct } from "../api/client";
import type { DeliveryMethod, ProductType, ProductView, ReturnRule } from "../api/types";
import { statusLabels, statusTagClassNames } from "./status";

const productTypeLabels: Record<ProductType, string> = {
  physical: "实物商品",
  virtual: "虚拟商品",
  creative: "创意商品",
};

const deliveryLabels: Record<DeliveryMethod, string> = {
  ems: "EMS",
  logistics: "物流",
  voucher: "电子凭证",
};

const returnLabels: Record<ReturnRule, string> = {
  seven_days: "七天无理由",
  no_returns: "不支持退货",
};

function MetaItem({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="ss-meta-item">
    <span className="ss-meta-label">{label}</span>
    <span className="ss-meta-value">{children}</span>
  </div>;
}

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

  const mainImage = product.images.find((image) => image.kind === "main");
  const galleryImages = product.images.filter((image) => image.kind === "gallery");

  return <main className="ss-page">
    <div className="ss-page-header">
      <div className="ss-page-header-left">
        <h1 className="ss-page-title">{product.title}</h1>
        <span className="ss-page-desc">
          商品 ID: {product.id} · 记录版本 v{product.version} · 字段模板 v{product.schema_version}
        </span>
      </div>
      <div className="ss-action-space" style={{ gap: 12 }}>
        <Link to="/products"><Button>返回商品列表</Button></Link>
        <Link to={`/products/${product.id}/edit`}><Button type="primary">编辑商品</Button></Link>
      </div>
    </div>

    <div className="ss-detail-layout">
      <div className="ss-detail-main">
        <section className="ss-form-section">
          <h2 className="ss-section-title">商品概览</h2>
          <div className="ss-section-body ss-meta-grid">
            <MetaItem label="短标题">{product.short_title || "-"}</MetaItem>
            <MetaItem label="商品类型">{productTypeLabels[product.product_type]}</MetaItem>
            <MetaItem label="价格（元）"><span className="ss-price-text">{product.price_amount}</span></MetaItem>
            <MetaItem label="库存">{product.stock}</MetaItem>
            <MetaItem label="状态"><span className={statusTagClassNames[product.status]}>{statusLabels[product.status]}</span></MetaItem>
            <MetaItem label="配送方式">{deliveryLabels[product.delivery_method] ?? product.delivery_method}</MetaItem>
            <MetaItem label="退货规则">{returnLabels[product.return_rule] ?? product.return_rule}</MetaItem>
            <MetaItem label="创建时间">{new Date(product.created_at).toLocaleString("zh-CN", { hour12: false })}</MetaItem>
            <MetaItem label="更新时间">{new Date(product.updated_at).toLocaleString("zh-CN", { hour12: false })}</MetaItem>
          </div>
        </section>

        <section className="ss-form-section">
          <h2 className="ss-section-title">图文信息</h2>
          <div className="ss-section-body">
            <div className="ss-detail-gallery">
              {product.images.length === 0 && <span className="ss-upload-hint">暂无商品图片</span>}
              {product.images.map((image, index) => (
                <Image
                  key={`${image.kind}-${image.sort_order}`}
                  width={96}
                  height={96}
                  style={{ objectFit: "cover", borderRadius: 8, border: "1px solid #eef1f6" }}
                  src={image.url}
                  alt={`${product.title}${image.kind === "main" ? "主图" : `图片${index + 1}`}`}
                />
              ))}
            </div>
            <div className="ss-meta-item" style={{ marginTop: 16 }}>
              <span className="ss-meta-label">商品描述</span>
              <p className="ss-detail-rich">{product.description_html || "-"}</p>
            </div>
          </div>
        </section>

        <section className="ss-form-section">
          <h2 className="ss-section-title">专属字段</h2>
          <div className="ss-section-body">
            <pre className="ss-detail-code">{JSON.stringify(product.attributes, null, 2)}</pre>
          </div>
        </section>
      </div>

      <aside className="ss-form-sidebar" style={{ top: 24 }}>
        <div className="ss-sidebar-card">
          <h3 className="ss-sidebar-title">状态与缓存说明</h3>
          <ul className="ss-sidebar-list">
            <li>公开详情接口只返回已上架商品，其他状态一律视为不存在</li>
            <li>状态仅允许「已上架 ↔ 已下架」互转，两者均可转为处罚</li>
            <li>处罚为终态，设置后不可再调整状态</li>
            <li>写操作使用记录版本做并发保护，成功后失效详情缓存</li>
            <li>字段模板按类型与版本存档，历史版本可安全回读</li>
          </ul>
        </div>
        <div className="ss-sidebar-card" style={{ marginTop: 16 }}>
          <h3 className="ss-sidebar-title">图片统计</h3>
          <ul className="ss-sidebar-list">
            <li>主图：{mainImage ? "已上传" : "未上传"}</li>
            <li>副图：{galleryImages.length} 张</li>
          </ul>
        </div>
      </aside>
    </div>
  </main>;
}
