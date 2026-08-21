import { ConfigProvider, Layout, Typography } from "antd";
import { Navigate, Route, Routes } from "react-router-dom";

import LoginPage from "../auth/LoginPage";
import RequireAuth from "../auth/RequireAuth";
import { adminTheme } from "./theme";

function ProductsPlaceholder() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header style={{ display: "flex", alignItems: "center", borderBottom: "1px solid #d9dfe8" }}>
        <Typography.Text strong style={{ fontSize: 18 }}>StockStack</Typography.Text>
      </Layout.Header>
      <Layout.Content style={{ padding: 24 }}>
        <main style={{ maxWidth: 1200, margin: "0 auto" }}>
          <Typography.Title level={1} style={{ marginTop: 0 }}>商品管理</Typography.Title>
          <Typography.Text type="secondary">商品列表将在后续任务中提供。</Typography.Text>
        </main>
      </Layout.Content>
    </Layout>
  );
}

export default function App() {
  return (
    <ConfigProvider theme={adminTheme}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/products"
          element={
            <RequireAuth>
              <ProductsPlaceholder />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/products" replace />} />
      </Routes>
    </ConfigProvider>
  );
}
