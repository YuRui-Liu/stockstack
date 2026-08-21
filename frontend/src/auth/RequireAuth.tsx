import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { ACCESS_TOKEN_KEY, UNAUTHORIZED_EVENT } from "../api/client";

interface RequireAuthProps {
  children: ReactNode;
}

export default function RequireAuth({ children }: RequireAuthProps) {
  const location = useLocation();
  const [token, setToken] = useState(() => sessionStorage.getItem(ACCESS_TOKEN_KEY));

  useEffect(() => {
    const handleUnauthorized = () => setToken(null);
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
  }, []);

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
