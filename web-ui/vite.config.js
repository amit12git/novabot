import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The proxy forwards /api/* to the FastAPI backend, so the browser
// only ever talks to localhost:5173 — no CORS issues in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
