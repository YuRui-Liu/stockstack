/// <reference types="vitest/config" />

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { configDefaults } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = process.env.VITE_DEV_PROXY_TARGET ?? env.VITE_DEV_PROXY_TARGET ?? "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": { target: proxyTarget, changeOrigin: true },
        "/uploads": { target: proxyTarget, changeOrigin: true },
      },
    },
    test: {
      environment: "jsdom",
      exclude: [...configDefaults.exclude, "e2e/**"],
      setupFiles: ["./src/test/setup.ts"],
    },
  };
});
