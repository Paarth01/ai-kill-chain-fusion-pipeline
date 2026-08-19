import { defineConfig } from "@playwright/test";

// No `webServer` here on purpose: this test needs BOTH the Python backend
// (uvicorn) and the Vite dev server running, and Playwright's webServer
// option only manages one process. CI (.github/workflows/ci.yml) starts
// both explicitly before running this; for local runs, do the same (see
// frontend section of the root README).
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
