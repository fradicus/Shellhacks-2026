import { expect, test as base } from "@playwright/test";
import path from "node:path";

const styleUrl = "https://tiles.openfreemap.org/styles/positron";
const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() !== "error") return;
      // Only the deliberately failed style request is allowed in the fallback test.
      if (testInfo.title.includes("failed basemap") && message.location().url === styleUrl &&
          message.text().includes("503")) return;
      errors.push(message.text());
    });
    // Keep smoke tests offline: exercise real MapLibre with an empty background style
    // and the installed matching worker. Tile quality/live provider uptime is not asserted.
    await page.route(styleUrl, (route) => route.fulfill({
      json: { version: 8, sources: {}, layers: [{ id: "background", type: "background" }] },
    }));
    await page.route("https://cdn.jsdelivr.net/npm/maplibre-gl@*/dist/maplibre-gl-worker.mjs", (route) =>
      route.fulfill({ path: path.resolve(__dirname, "../../web/node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs"),
        contentType: "text/javascript" }));
    await use(page);
    expect(errors, "Browser console errors and uncaught exceptions").toEqual([]);
  },
});

test("every navigation route returns 200 and renders without console errors", async ({ page }) => {
  expect((await page.goto("/"))?.status()).toBe(200);
  const nav = page.getByRole("navigation", { name: "Main" });
  const hrefs = await nav.getByRole("link").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
  expect(hrefs).toEqual(["/", "/changes", "/coverage", "/gemini", "/impact"]);
  for (const href of hrefs) {
    expect((await page.goto(href!))?.status(), href!).toBe(200);
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" }).locator('[aria-current="page"]')).toHaveCount(1);
  }
});

test("six historical pairs rank correctly, select on map, and open evidence", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Sample data (fixture mode)")).toBeVisible();
  await expect(page.getByRole("button", { name: "Historical (6)", exact: true })).toHaveAttribute("aria-pressed", "true");
  const list = page.getByRole("region", { name: "Ranked overlaps" });
  const rows = list.getByRole("listitem");
  await expect(rows).toHaveCount(6);
  const pairs = ["DESC:DESC_3__GPC:GPC_2", "DESC:DESC_3__GPC:GPC_3", "DESC:DESC_2__GPC:GPC_1",
    "DESC:DESC_1__GPC:GPC_1", "DESC:DESC_5__GPC:GPC_2", "DESC:DESC_5__GPC:GPC_3"];
  for (const [index, pair] of pairs.entries()) {
    await expect(rows.nth(index).getByRole("link", { name: /Evidence/ })).toHaveAttribute("href", `/pair/${encodeURIComponent(pair)}`);
  }
  const select = rows.first().getByRole("button", { name: /Show on map/ });
  await select.click();
  await expect(select).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("5.65 mi center-to-center, not a route", { exact: true })).toBeVisible();
  await rows.first().getByRole("link", { name: /Evidence/ }).click();
  await expect(page).toHaveURL(new RegExp(`/pair/${encodeURIComponent(pairs[0])}$`));
  await expect(page.getByRole("main")).toBeVisible();
  // F11 owns drawer content; its placeholder is still a valid reachable route.
  expect((await page.request.get(page.url())).status()).toBe(200);
});

test("failed basemap preserves overlaps, selection, and accessible project table", async ({ page }) => {
  await page.route(styleUrl, (route) => route.fulfill({ status: 503, body: "Injected basemap failure" }));
  await page.goto("/");
  await expect(page.getByRole("status").filter({ hasText: "Basemap tiles failed to load" })).toBeVisible();
  const rows = page.getByRole("region", { name: "Ranked overlaps" }).getByRole("listitem");
  await expect(rows).toHaveCount(6);
  await rows.first().getByRole("button").click();
  await expect(rows.first().getByRole("button")).toHaveAttribute("aria-pressed", "true");
  await page.getByText("All projects (10), as a table", { exact: true }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(10);
  await expect(page.getByRole("link", { name: "OpenStreetMap", exact: true })).toBeVisible();
});
