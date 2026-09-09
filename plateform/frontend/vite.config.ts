import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
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