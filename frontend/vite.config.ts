import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/tracks": "http://localhost:8000",
      "/history": "http://localhost:8000",
      "/stream": "http://localhost:8000",
      "/ew": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    // e2e/ contains Playwright specs (different test API, run via
    // `npx playwright test`) — excluded here so Vitest doesn't try to
    // execute them itself and fail on the API mismatch.
    exclude: ["**/node_modules/**", "**/e2e/**"],
  },
});
