import { Button, ConfigProvider, Layout, Typography } from "antd";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";

import LoginPage from "../auth/LoginPage";
import RequireAuth from "../auth/RequireAuth";
import ProductFormPage from "../products/ProductFormPage";
import ProductDetailPage from "../products/ProductDetailPage";
import ProductListPage from "../products/ProductListPage";
import { adminTheme } from "./theme";

function ProductCreator() {
  const navigate = useNavigate();
  return <ProductFormPage onSaved={() => navigate("/products", { replace: true })} />;
}

function ProductEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  return <ProductFormPage productId={id} onSaved={() => navigate("/products", { replace: true })} />;
}

function ProductsLayout({ children }: { children: React.ReactNode }) {
  return (
    <Layout className="app-shell">
      <Layout.Header className="app-header">
        <Link to="/products" className="app-brand" aria-label="快手 StockStack 商品管理首页">
          <img className="app-brand-logo" src="/brand/kuaishou-logo.png" alt="快手" />
          <span className="app-brand-divider" aria-hidden="true" />
          <Typography.Text className="app-brand-name">StockStack</Typography.Text>
        </Link>
        <nav className="app-header-nav" aria-label="主导航"><Link to="/products" className="app-nav-link">商品管理</Link><Link to="/products/new"><Button type="primary">发布商品</Button></Link></nav>
      </Layout.Header>
      <Layout.Content className="app-content">{children}</Layout.Content>
    </Layout>
  );
}

function protectedPage(children: React.ReactNode) {
  return <RequireAuth><ProductsLayout>{children}</ProductsLayout></RequireAuth>;
}

export default function App() {
  return (
    <ConfigProvider theme={adminTheme}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/products" element={protectedPage(<ProductListPage />)} />
        <Route path="/products/new" element={protectedPage(<ProductCreator />)} />
        <Route path="/products/:id" element={protectedPage(<ProductDetailPage />)} />
        <Route path="/products/:id/edit" element={protectedPage(<ProductEditor />)} />
        <Route path="*" element={<Navigate to="/products" replace />} />
      </Routes>
    </ConfigProvider>
  );
}
