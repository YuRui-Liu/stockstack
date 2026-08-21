import { ConfigProvider, Layout } from "antd";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";

import LoginPage from "../auth/LoginPage";
import RequireAuth from "../auth/RequireAuth";
import ProductFormPage from "../products/ProductFormPage";
import ProductDetailPage from "../products/ProductDetailPage";
import ProductListPage from "../products/ProductListPage";
import { adminTheme } from "./theme";
import "./design.css";

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
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header className="ss-app-header">
        <Link to="/products" className="ss-app-brand">
          <span className="ss-app-brand-dot" aria-hidden="true" />
          StockStack
        </Link>
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
