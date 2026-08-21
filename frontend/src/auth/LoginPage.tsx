import { Alert, Button, Card, Form, Input, Space, Typography } from "antd";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ACCESS_TOKEN_KEY, ApiError, login } from "../api/client";
import type { LoginRequest } from "../api/types";

interface LoginLocationState {
  from?: { pathname?: string };
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();

  if (sessionStorage.getItem(ACCESS_TOKEN_KEY)) return <Navigate to="/products" replace />;

  const handleSubmit = async (credentials: LoginRequest) => {
    setSubmitting(true);
    setErrorMessage(undefined);
    try {
      const response = await login(credentials);
      sessionStorage.setItem(ACCESS_TOKEN_KEY, response.access_token);
      const state = location.state as LoginLocationState | null;
      navigate(state?.from?.pathname ?? "/products", { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.response.message : "登录失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main
      style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, background: "#f5f7fa" }}
    >
      <Card style={{ width: "100%", maxWidth: 400 }}>
        <Space direction="vertical" size={4} style={{ width: "100%", marginBottom: 24 }}>
          <Typography.Text strong style={{ color: "#1677ff" }}>StockStack</Typography.Text>
          <Typography.Title level={1} style={{ fontSize: 28, margin: 0 }}>管理员登录</Typography.Title>
          <Typography.Text type="secondary">登录后管理商品信息与发布状态</Typography.Text>
        </Space>

        {errorMessage ? <Alert type="error" showIcon role="alert" message={errorMessage} style={{ marginBottom: 16 }} /> : null}

        <Form<LoginRequest> layout="vertical" requiredMark={false} onFinish={handleSubmit}>
          <Form.Item name="username" label="管理员账号" rules={[{ required: true, message: "请输入管理员账号" }]}>
            <Input autoFocus autoComplete="username" disabled={submitting} />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password autoComplete="current-password" disabled={submitting} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting} block>
            登录
          </Button>
        </Form>
      </Card>
    </main>
  );
}
