import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/tracks": "http://localhost:8000",
      "/stream": "http://localhost:8000",
      "/ew": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
