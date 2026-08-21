import { Alert, Button, Form, Input, Typography } from "antd";
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
    <main className="login-page">
      <section className="login-visual" aria-label="StockStack 商品管理平台">
        <div className="login-brand">
          <img className="login-brand-logo" src="/brand/kuaishou-logo.png" alt="快手" />
          <span className="login-product-name">StockStack 商品管理</span>
        </div>
        <div className="login-copy"><h1>让商品管理<br />更简单、更清晰</h1><p>从发布、库存到上下架状态，在一个工作台中高效完成。</p></div>
      </section>
      <section className="login-panel">
      <div className="login-form-wrap">
        <Typography.Title className="login-title" level={1}>管理员登录</Typography.Title>
        <Typography.Text className="login-caption">欢迎回来，请登录 StockStack 管理后台</Typography.Text>

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
      </div>
      </section>
    </main>
  );
}
