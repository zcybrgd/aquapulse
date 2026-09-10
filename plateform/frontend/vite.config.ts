import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: {
      "/pipeline-lab-proxy": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
        rewrite: (path) =>
          path.replace(/^\/pipeline-lab-proxy/, ""),
      },
    },
  },
});