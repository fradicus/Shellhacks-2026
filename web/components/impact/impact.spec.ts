import { expect, test, type Page } from "@playwright/test";

// SYNTHETIC TEST DATA ONLY. Our own /api routes are mocked so the flow runs offline and deterministically.
const days = 3653;
const history = {
  origin: "committed", window: { start: "2016-01-01", end: "2025-12-31" }, citation: "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
  rain: { id: "USW00000001", name: "SYNTHETIC TEST STATION", distance_mi: 3.2, source_url: "https://www.ncei.noaa.gov/access/services/data/v1?stations=USW00000001" }, wind: null,
  // Rain on every 5th day, so each replayed year loses some workdays.
  prcp_in: Array.from({ length: days }, (_, i) => (i % 5 === 0 ? 1 : 0)), tmax_f: Array(days).fill(70), tmin_f: Array(days).fill(50), snow_in: Array(days).fill(0), wsf2_mph: null,
};
const recentStart = new Date(Date.now() - 400 * 86_400_000).toISOString().slice(0, 10);
const recent = { start: recentStart, end: new Date(Date.now() - 86_400_000).toISOString().slice(0, 10), source_url: "https://www.ncei.noaa.gov/access/services/data/v1?stations=USW00000001",
  prcp_in: Array.from({ length: 400 }, (_, i) => (i % 4 === 0 ? 0.8 : 0)), tmax_f: Array(400).fill(72), tmin_f: Array(400).fill(51), snow_in: Array(400).fill(0), wsf2_mph: null };

async function mockApis(page: Page) {
  await page.route("**/api/geocode?*", (r) => r.fulfill({ json: { query: "Test Town", result: { label: "Test Town, SC", lat: 32.3, lon: -81.0, source: "OpenStreetMap Nominatim", attribution: "© OpenStreetMap contributors (ODbL)" } } }));
  await page.route("**/api/weather-history/recent?*", (r) => r.fulfill({ json: { recent } }));
  await page.route("**/api/weather-history?*", (r) => r.fulfill({ json: { request: { lat: 32.3, lon: -81 }, history } }));
  await page.route("**/api/operations/water?*", (r) => r.fulfill({ status: 503, json: { error: "synthetic outage" } }));
  await page.route("**/api/operations/site?*", (r) => r.fulfill({ status: 503, json: { error: "synthetic outage" } }));
}

test("search a place, pick a start date on the calendar, get the report and download a PDF", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mockApis(page);
  await page.goto("/impact");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Pick a site");
  await expect(page.getByRole("link", { name: "Mobilization" })).toHaveCount(0);
  await page.getByLabel("Search a place or address").fill("Test Town");
  await page.getByRole("button", { name: "Go", exact: true }).click();
  await expect(page.getByText("Found via OpenStreetMap Nominatim", { exact: false })).toBeVisible();
  await expect(page.getByText("SYNTHETIC TEST STATION", { exact: false }).first()).toBeVisible();
  // Water and soil failed on purpose; the report still works.
  await expect(page.getByText("Water:", { exact: false }).first()).toBeVisible();
  const day = page.getByRole("gridcell").filter({ hasText: /^15$/ }).first();
  await day.click();
  await expect(page.getByText("Normal finish", { exact: true })).toBeVisible();
  await expect(page.getByText(/Typical weather · median of \d+ years/)).toBeVisible();
  await page.getByLabel("Cost of one delay day · USD").fill("1000");
  await expect(page.getByText(/\$[\d,]+\.00/).first()).toBeVisible();
  await expect(page.getByText("How it was this time last year", { exact: true })).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF", exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^site-weather-report-\d{4}-\d{2}-\d{2}\.pdf$/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test("pair context still attaches through the picker and missing IDs remain explicit", async ({ page }) => {
  await mockApis(page);
  await page.goto("/impact");
  const select = page.getByLabel("Project pair (optional)");
  const id = await select.locator("option").nth(1).getAttribute("value");
  expect(id).toBeTruthy();
  await select.selectOption(id!);
  await page.getByRole("button", { name: "Open worksheet", exact: true }).click();
  await expect(page.getByRole("link", { name: "Inspect pair evidence and review details" })).toBeVisible();
  await page.goto("/impact?pair=missing-pair");
  await expect(page.getByText("The requested pair was not found", { exact: false })).toBeVisible();
});
