import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Single-port dev: Vite on 3000 serves the UI and proxies API/webhook paths
// to FastAPI on 8000. That way one ngrok tunnel exposes the whole stack.
// API prefixes the backend owns:
const BACKEND_PREFIXES = [
  "/auth",
  "/admin",
  "/voice",
  "/calls",
  "/campaigns",
  "/contacts",
  "/conversations",
  "/labels",
  "/saved-replies",
  "/faqs",
  "/huawei",
  "/metrics",
  "/health",
  "/integrations",
  "/telephony",
  "/docs",
  "/openapi.json",
  "/redoc",
];
const proxy = Object.fromEntries(
  BACKEND_PREFIXES.map((p) => [p, { target: "http://127.0.0.1:8000", changeOrigin: true }]),
);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    strictPort: true,
    // Allow ngrok-tunneled hosts in dev so the browser can hit https://*.ngrok-free.app.
    allowedHosts: [".ngrok-free.app", ".ngrok-free.dev", ".ngrok.app", ".ngrok.io", ".ngrok.dev"],
    proxy,
  },
  preview: {
    port: 3000,
    host: true,
  },
});
