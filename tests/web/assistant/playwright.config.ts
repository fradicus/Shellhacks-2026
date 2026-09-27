import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".", testMatch: "assistant.spec.ts", timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    viewport: { width: 1440, height: 1000 },
    timezoneId: "America/New_York",
    trace: "retain-on-failure",
  },
  reporter: "line",
});
