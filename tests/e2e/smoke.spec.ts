import { expect, test as base } from "@playwright/test";
import path from "node:path";
import { cell, toCsv } from "../../web/app/api/export/csv";

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
  expect((await page.goto("/map"))?.status()).toBe(200);
  const nav = page.getByRole("navigation", { name: "Main" });
  const hrefs = await nav.getByRole("link").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
  expect(hrefs).toEqual(expect.arrayContaining(["/", "/time", "/changes", "/coverage", "/gemini", "/impact"]));
  expect(new Set(hrefs).size, "Navigation destinations are unique").toBe(hrefs.length);
  for (const href of hrefs) {
    expect(href, "Navigation stays inside the app").toMatch(/^\/(?:[a-z0-9-]+\/?)*$/);
    expect((await page.goto(href!))?.status(), href!).toBe(200);
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    if (href === "/") {
      await expect(page.getByRole("link", { name: "Launch explorer", exact: true })).toHaveAttribute("href", "/time");
    } else {
      await expect(page.getByRole("navigation", { name: "Main" }).locator('[aria-current="page"]')).toHaveCount(1);
    }
  }
});

test("six historical pairs rank correctly, select on map, and open evidence", async ({ page }) => {
  await page.goto("/map");
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
  await expect(page.getByRole("region", { name: "Coordination card" })).toBeVisible();
  expect((await page.request.get(page.url())).status()).toBe(200);
});

test("pair evidence preserves sponsor facts, missing briefs, and review uncertainty", async ({ page }) => {
  const pair = "DESC:DESC_3__GPC:GPC_2";
  expect((await page.goto(`/pair/${encodeURIComponent(pair)}`))?.status()).toBe(200);
  const card = page.getByRole("region", { name: "Coordination card" });
  await expect(card).toContainText("5.65 mi");
  await expect(card).toContainText("in service 152 days apart");
  await expect(card).toContainText("Brief unavailable");
  await expect(card).toContainText("milestone, not a construction window");
  await expect(card).toContainText("Needs review");
  await expect(page.getByText("Reviewed", { exact: true })).toHaveCount(0);
  const desc = page.getByRole("article", { name: "Jasper - Okatie 230 kV #2: Construct" });
  const gpc = page.getByRole("article", { name: "SAV: MCINTOSH - PURRYSBURG 230KV REACTORS" });
  await expect(desc).toContainText("exact date 2025-12-31");
  await expect(desc).toContainText("mean of two located endpoints");
  await expect(gpc).toContainText("exact date 2026-06-01");
  await expect(gpc).toContainText("from one located endpoint");
  for (const panel of [desc, gpc]) {
    await expect(panel).toContainText("Projects_Overlaps.xlsx");
    await expect(panel).toContainText("Not published");
  }
  await expect(card.getByRole("link", { name: "Impact inputs" })).toHaveAttribute("href", `/impact?pair=${encodeURIComponent(pair)}`);
});

test("print invokes the browser and preserves the card and citations", async ({ page }) => {
  await page.addInitScript(() => {
    window.print = () => { document.documentElement.dataset.printRequested = "true"; };
  });
  await page.goto(`/pair/${encodeURIComponent("DESC:DESC_3__GPC:GPC_2")}`);
  await page.getByRole("button", { name: "Print card" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-print-requested", "true");
  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("navigation", { name: "Main" })).toBeHidden();
  await expect(page.getByRole("button", { name: "Print card" })).toBeHidden();
  await expect(page.getByRole("region", { name: "Coordination card" })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(2);
  for (const panel of await page.getByRole("article").all()) {
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("Projects_Overlaps.xlsx");
  }
});

test("CSV exports contain source and uncertainty fields and filter historical matches", async ({ request }) => {
  const response = await request.get("/api/export?type=matches&view=historical");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("text/csv");
  expect(response.headers()["content-disposition"]).toContain("gridbridge-matches-historical.csv");
  const csv = await response.text();
  const rows = csv.trimEnd().split("\r\n");
  expect(rows).toHaveLength(7); // Sponsor fixture contains no multiline fields.
  expect(rows[0]).toContain("a_in_service_precision,a_location_confidence,a_center_basis,a_source_id,a_source_page");
  expect(rows[1]).toContain("1,DESC:DESC_3__GPC:GPC_2,historical,<10 mi,5.650181138667416,5.65,152,needs_review");
  expect(rows.slice(1).every((row) => row.includes("sperry-sample"))).toBe(true);
  const future = await request.get("/api/export?type=matches&view=future");
  expect(future.status()).toBe(200);
  expect((await future.text()).trimEnd().split("\r\n")).toHaveLength(1);
  const projects = await request.get("/api/export?type=projects");
  expect(projects.status()).toBe(200);
  const projectCsv = await projects.text();
  expect(projectCsv.trimEnd().split("\r\n")).toHaveLength(11);
  expect(projectCsv).toContain("center_basis,location_confidence,source_id,source_page,active");
  expect(projectCsv).toContain("not published");
});

test("CSV export rejects invalid query parameters", async ({ request }) => {
  for (const query of ["", "?type=other", "?type=matches&view=other", "?type=matches&limit=1"]) {
    const response = await request.get(`/api/export${query}`);
    expect(response.status(), query).toBe(400);
    expect((await response.json()).error).toBe("invalid query");
  }
});

test("CSV neutralizes spreadsheet formulas and escapes quotes and newlines", async () => {
  for (const value of ["=1+1", "+cmd", "-cmd", "@SUM(A1)", "\tcmd", "\rcmd"]) {
    // Remove CSV quoting to inspect the literal cell prefix, independently of serialization.
    expect(cell(value).replace(/^"/, "").startsWith("'")).toBe(true);
  }
  expect(cell(-81.2)).toBe("-81.2");
  expect(cell(0)).toBe("0");
  expect(cell(null)).toBe("");
  expect(toCsv(["name", "count"], [['A, "quoted"\nname', 2]])).toBe('name,count\r\n"A, ""quoted""\nname",2\r\n');
});

test("filing history cites both public pages and filters to an honest empty state", async ({ page }) => {
  await page.goto("/changes");
  await expect(page.getByText("DESC:0139 M,N", { exact: true })).toBeVisible();
  await expect(page.getByText("2024-12-31", { exact: true })).toBeVisible();
  await expect(page.getByText("2026-05-31", { exact: true })).toBeVisible();
  await expect(page.getByText("historical", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "DESC filing 2024-2028, p. 3" })).toHaveAttribute(
    "href", "https://www.scrtp.com/assets/pdfs/home/2024-2028-2million-and-above-project-descriptions.pdf#page=3");
  await expect(page.getByRole("link", { name: "DESC filing 2025-2029, p. 2" })).toHaveAttribute(
    "href", "https://www.scrtp.com/assets/pdfs/home/2025-2029-2million-and-above-project-descriptions.pdf#page=2");
  await page.getByRole("button", { name: "Cost (0)", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("No filing changes");
  await expect(page.getByRole("status")).toContainText("No changes for this field.");
  await page.getByRole("button", { name: "In-service date (1)", exact: true }).click();
  await expect(page.getByText("DESC:0139 M,N", { exact: true })).toBeVisible();
});

test("failed basemap preserves overlaps, selection, and accessible project table", async ({ page }) => {
  await page.route(styleUrl, (route) => route.fulfill({ status: 503, body: "Injected basemap failure" }));
  await page.goto("/map");
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


test("landing controls work and the explorer returns to a working landing page", async ({ page }) => {
  await page.goto("/");
  // Brand-first reference hero ("GridBridge") or the prior marketing headline.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/GridBridge|Every mile/);
  const network = page.getByRole("button", { name: "02 The network", exact: true });
  await network.click();
  await expect(network).toHaveAttribute("aria-pressed", "true");
  // Caption is a text node beside siblings; avoid exact-on-element matching.
  await expect(page.getByText("One network.")).toBeVisible();
  await page.getByRole("button", { name: "Pause animation", exact: true }).click();
  await expect(page.getByRole("button", { name: "Play animation", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("link", { name: "Launch explorer", exact: true }).click();
  await expect(page).toHaveURL(/\/time$/);
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(page.getByRole("button", { name: "01 The road", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Pause animation", exact: true }).click();
  await expect(page.getByRole("button", { name: "Play animation", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
