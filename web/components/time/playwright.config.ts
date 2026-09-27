import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: ".", testMatch: "payload.spec.ts", timeout: 60_000,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000", reducedMotion: "reduce", trace: "retain-on-failure" },
  reporter: "line",
});
