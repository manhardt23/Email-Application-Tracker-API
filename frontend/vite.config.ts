import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server proxies API + stats to the FastAPI backend so the SPA can run
// same-origin in development. In production the build is served by FastAPI
// from frontend/dist, so these proxies are dev-only.
const BACKEND = process.env.VITE_BACKEND_ORIGIN ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/stats": { target: BACKEND, changeOrigin: true },
    },
  },
});
