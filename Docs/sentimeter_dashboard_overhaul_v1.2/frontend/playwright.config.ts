import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: "http://localhost:3000",
    screenshot: "only-on-failure",
    trace: "on-first-retry"
  },
  reporter: [["html", { outputFolder: "test-artifacts/playwright-report" }]]
});
