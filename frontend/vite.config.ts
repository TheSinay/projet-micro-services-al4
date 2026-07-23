/// <reference types="vitest/config" />
import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api/v1/users/health": {
        target: "http://localhost:8001",
        rewrite: () => "/health",
        changeOrigin: true,
      },
      "/api/v1/restaurants/health": {
        target: "http://localhost:8002",
        rewrite: () => "/health",
        changeOrigin: true,
      },
      "/api/v1/orders/health": {
        target: "http://localhost:8003",
        rewrite: () => "/health",
        changeOrigin: true,
      },
      "/api/v1/payments/health": {
        target: "http://localhost:8004",
        rewrite: () => "/health",
        changeOrigin: true,
      },
      "/api/v1/deliveries/health": {
        target: "http://localhost:8005",
        rewrite: () => "/health",
        changeOrigin: true,
      },
      "/api/v1/notifications/health": {
        target: "http://localhost:8006",
        rewrite: () => "/health",
        changeOrigin: true,
      },
      "/api/v1/auth": { target: "http://localhost:8001", changeOrigin: true },
      "/api/v1/users": { target: "http://localhost:8001", changeOrigin: true },
      "/api/v1/restaurants": { target: "http://localhost:8002", changeOrigin: true },
      "/api/v1/orders": { target: "http://localhost:8003", changeOrigin: true },
      "/api/v1/carts": { target: "http://localhost:8003", changeOrigin: true },
      "/api/v1/payments": { target: "http://localhost:8004", changeOrigin: true },
      "/api/v1/_chaos": { target: "http://localhost:8004", changeOrigin: true },
      "/api/v1/deliveries": { target: "http://localhost:8005", changeOrigin: true },
      "/api/v1/couriers": { target: "http://localhost:8005", changeOrigin: true },
      "/api/v1/kitchen-tickets": { target: "http://localhost:8002", changeOrigin: true },
      "/api/v1/notifications": { target: "http://localhost:8006", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
