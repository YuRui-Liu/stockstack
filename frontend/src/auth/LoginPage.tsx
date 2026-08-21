import { Alert, Button, Card, Form, Input, Space, Typography } from "antd";
import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate, type Location, type To } from "react-router-dom";

import { ACCESS_TOKEN_KEY, ApiError, login } from "../api/client";
import type { LoginRequest } from "../api/types";

interface LoginLocationState {
  from?: Location;
}

function internalDestination(state: unknown): To {
  const from = (state as LoginLocationState | null)?.from;
  if (!from || !from.pathname.startsWith("/") || from.pathname.startsWith("//")) return "/products";
  return { pathname: from.pathname, search: from.search, hash: from.hash };
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();
  const errorSummaryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (errorMessage) errorSummaryRef.current?.focus();
  }, [errorMessage]);

  if (sessionStorage.getItem(ACCESS_TOKEN_KEY)) return <Navigate to="/products" replace />;

  const handleSubmit = async (credentials: LoginRequest) => {
    setSubmitting(true);
    setErrorMessage(undefined);
    try {
      const response = await login(credentials);
      sessionStorage.setItem(ACCESS_TOKEN_KEY, response.access_token);
      navigate(internalDestination(location.state), { replace: true });
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

        {errorMessage ? (
          <div ref={errorSummaryRef} tabIndex={-1} role="alert" style={{ marginBottom: 16 }}>
            <Alert type="error" showIcon role="presentation" message={errorMessage} />
          </div>
        ) : null}

        <Form<LoginRequest>
          layout="vertical"
          requiredMark={false}
          scrollToFirstError={{ focus: true }}
          onFinish={handleSubmit}
        >
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
