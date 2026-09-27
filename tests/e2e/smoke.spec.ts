import { expect, test as base } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { cell, toCsv } from "../../web/app/api/export/csv";

// Expected pairs come from the fixture the app serves, so a rule or fixture change (C41) never needs new ids here.
interface FixtureMatch { _id: string; a: string; b: string; view: string; band: 0 | 1; rank: number;
  distance_mi: number; drive_mi?: number | null; time_gap_days: number | null }
interface FixtureProject { project_key: string; name: string; in_service: { date: string | null };
  center: { basis: "one" | "two" } | null }
function fixture<T>(name: string): T {
  return JSON.parse(readFileSync(path.resolve(__dirname, `../../data/fixtures/${name}.json`), "utf8")) as T;
}
const historical = fixture<FixtureMatch[]>("matches").filter((m) => m.view === "historical").sort((x, y) => x.rank - y.rank);
const projects = new Map(fixture<FixtureProject[]>("projects").map((p) => [p.project_key, p]));
const top = historical[0];

const styleUrl = "https://tiles.openfreemap.org/styles/positron";
// Overlaps (/time) draws on the dark style; stub it the same way.
const darkStyleUrl = "https://tiles.openfreemap.org/styles/dark";
const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() !== "error") return;
      // Only the deliberately failed style request is allowed in the fallback test.
      if (testInfo.title.includes("failed basemap") && [styleUrl, darkStyleUrl].includes(message.location().url) &&
          message.text().includes("503")) return;
      errors.push(message.text());
    });
    // Keep smoke tests offline: exercise real MapLibre with an empty background style
    // and the installed matching worker. Tile quality/live provider uptime is not asserted.
    for (const url of [styleUrl, darkStyleUrl]) await page.route(url, (route) => route.fulfill({
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
  // Loads every nav route in turn; cold /time and /history builds alone can take most of the default 30s.
  test.setTimeout(60_000);
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
    await expect(page.getByRole("navigation", { name: "Main" }).locator('[aria-current="page"]')).toHaveCount(1);
  }
});

// /map was retired (C35) and redirects to /time; the sponsor pairs now live in its Legacy pairs list.
test("fixture historical pairs rank correctly, select on the Overlaps map, and open evidence", async ({ page }) => {
  await page.goto("/time");
  await expect(page.getByText("Sample data · fixture mode")).toBeVisible();
  const list = page.getByRole("navigation", { name: "Overlap pairs" });
  await list.getByRole("button", { name: "Legacy pairs", exact: true }).click();
  await expect(list.getByRole("button", { name: `Historical ${historical.length}`, exact: true })).toHaveAttribute("aria-pressed", "true");
  const rows = list.locator("ol > li > button");
  await expect(rows).toHaveCount(historical.length);
  const pairs = historical.map((m) => m._id);
  for (const [index, pair] of pairs.entries()) {
    // Each row's title leads with its two project keys, in stored rank order.
    await expect(rows.nth(index)).toHaveAttribute("title", new RegExp(`^${pair.replace("__", " · ")} · `));
  }
  await rows.first().click();
  await expect(rows.first()).toHaveAttribute("aria-pressed", "true");
  const detail = page.getByRole("complementary", { name: "Selected pair" });
  await expect(detail).toContainText(`${(top.drive_mi ?? top.distance_mi).toFixed(2)}`);
  await expect(detail).toContainText(/miles (apart, center to center|by road)/);
  const evidence = detail.getByRole("link", { name: /Open evidence/ });
  await expect(evidence).toHaveAttribute("href", `/pair/${encodeURIComponent(pairs[0])}`);
  await evidence.click();
  await expect(page).toHaveURL(new RegExp(`/pair/${encodeURIComponent(pairs[0])}$`));
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("region", { name: "Coordination card" })).toBeVisible();
  expect((await page.request.get(page.url())).status()).toBe(200);
});

test("pair evidence preserves sponsor facts, missing briefs, and review uncertainty", async ({ page }) => {
  const pair = top._id;
  expect((await page.goto(`/pair/${encodeURIComponent(pair)}`))?.status()).toBe(200);
  const card = page.getByRole("region", { name: "Coordination card" });
  await expect(card).toContainText(`${top.distance_mi.toFixed(2)} mi`);
  if (top.time_gap_days !== null) await expect(card).toContainText(`in service ${top.time_gap_days} days apart`);
  await expect(card).toContainText("Brief unavailable");
  await expect(card).toContainText("milestone, not a construction window");
  await expect(card).toContainText("Needs review");
  await expect(page.getByText("Reviewed", { exact: true })).toHaveCount(0);
  for (const key of [top.a, top.b]) {
    const project = projects.get(key)!;
    const panel = page.getByRole("article", { name: project.name });
    await expect(panel).toContainText(`exact date ${project.in_service.date}`);
    await expect(panel).toContainText(project.center?.basis === "one" ? "from one located endpoint" : "mean of two located endpoints");
    await expect(panel).toContainText("Projects_Overlaps.xlsx");
    await expect(panel).toContainText("Not published");
  }
  await expect(card.getByRole("link", { name: "Impact inputs" })).toHaveAttribute("href", `/impact?pair=${encodeURIComponent(pair)}`);
});

test("print invokes the browser and preserves the card and citations", async ({ page }) => {
  await page.addInitScript(() => {
    window.print = () => { document.documentElement.dataset.printRequested = "true"; };
  });
  await page.goto(`/pair/${encodeURIComponent(top._id)}`);
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
  expect(rows).toHaveLength(historical.length + 1); // Sponsor fixture contains no multiline fields.
  expect(rows[0]).toContain("a_in_service_precision,a_location_confidence,a_center_basis,a_source_id,a_source_page");
  expect(rows[1]).toContain([top.rank, top._id, "historical", top.band === 0 ? "<10 mi" : "10-25 mi", top.distance_mi,
    top.distance_mi.toFixed(2), top.time_gap_days ?? "", "needs_review"].join(","));
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
  await page.route(darkStyleUrl, (route) => route.fulfill({ status: 503, body: "Injected basemap failure" }));
  await page.goto("/time");
  await expect(page.getByRole("status").filter({ hasText: "Basemap tiles failed to load" })).toBeVisible();
  const list = page.getByRole("navigation", { name: "Overlap pairs" });
  await list.getByRole("button", { name: "Legacy pairs", exact: true }).click();
  const rows = list.locator("ol > li > button");
  await expect(rows).toHaveCount(historical.length);
  await rows.first().click();
  await expect(rows.first()).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("complementary", { name: "Selected pair" })).toContainText(`${(top.drive_mi ?? top.distance_mi).toFixed(2)}`);
  await page.getByRole("region", { name: "All projects" }).getByRole("button").click();
  const drawer = page.getByRole("complementary", { name: "All projects" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("listitem")).toHaveCount(10);
});


test("landing controls work and the explorer returns to a working landing page", async ({ page }) => {
  await page.goto("/");
  // Common Ground truck hero or older GridBridge stacks.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Common Ground|GridBridge|Every mile/);
  const network = page.getByRole("button", { name: "02 The network", exact: true });
  if (await network.isVisible()) {
    await network.click();
    await expect(network).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("One region. More possibilities.")).toBeVisible();
  } else {
    // Truck-only Common Ground hero (no map toggle). Caption beat line stays visible on mobile.
    await expect(page.getByText("Same roads. One network.")).toBeVisible();
  }
  await page.getByRole("button", { name: "Pause animation", exact: true }).click();
  await expect(page.getByRole("button", { name: "Play animation", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("link", { name: "Explore overlaps", exact: true }).click();
  await expect(page).toHaveURL(/\/time$/);
  await page.getByRole("link", { name: "Home", exact: true }).click();
  if (await page.getByRole("button", { name: "01 The road", exact: true }).isVisible()) {
    await expect(page.getByRole("button", { name: "01 The road", exact: true })).toHaveAttribute("aria-pressed", "true");
  }
  await page.getByRole("button", { name: "Pause animation", exact: true }).click();
  await expect(page.getByRole("button", { name: "Play animation", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
