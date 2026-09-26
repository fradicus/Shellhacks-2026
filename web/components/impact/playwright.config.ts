import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "impact.spec.ts",
  outputDir: process.env.F17_TEST_OUTPUT ?? "../../../test-results/impact",
  reporter: "list",
  use: { baseURL: process.env.BASE_URL ?? "http://localhost:3017" },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1100 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 } } },
  ],
});
