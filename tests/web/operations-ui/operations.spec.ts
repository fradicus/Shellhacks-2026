import { expect, test, type Page, type TestInfo } from "@playwright/test";

const stamp = "2026-09-26T16:00:00Z";
const point = { lat: 47.6062, lon: -122.3321 };
const sources: Record<string, string> = { weather: "https://api.weather.gov", soil: "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
  roadwork: "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed", route: "https://routes.googleapis.com/directions/v2:computeRoutes",
  aef: "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL" };
const emptyEnvelope = (provider: string, status: string, reason: string) => ({
  schema_version: "operations-v1", provider, status, request_hash: "synthetic-request", retrieved_at: stamp,
  source_updated_at: null, valid_from: null, valid_to: null, source_url: sources[provider],
  source_version: "synthetic-test-only", evidence_hash: null,
  coverage: { requested: 1, completed: 0, failed: 1, truncated: false }, data: null, limitations: [reason],
});
const weather = {
  ...emptyEnvelope("weather", "available", "Synthetic test-only weather."), evidence_hash: "a".repeat(64),
  coverage: { requested: 1, completed: 1, failed: 0, truncated: false },
  data: { scope: "Synthetic test-only point forecast.", samples: [{ point, updated_at: stamp, alerts_checked_at: stamp,
    alert_coverage: "point_county_and_zone", alerts: [], forecast: [{ start: stamp, end: "2026-09-26T17:00:00Z",
      temperature: 61, temperature_unit: "F", wind_speed: "8 mph", wind_direction: "SW", precipitation_probability: 12,
      description: "Synthetic test-only clouds" }] }] },
};
const roadwork = emptyEnvelope("roadwork", "out_of_coverage", "Synthetic test-only: outside supported road-work coverage.");
const reference = {
  schema_version: "operations-v1", aef_years: [2025], hazmat: ["EXPLOSIVES"],
  limits: { route_samples: 5, route_sample_max_gap_km: 25, max_departure_days: 7 },
  providers: [
    { id: "weather", ready: true, jurisdictions: ["Synthetic test only"], refresh_seconds: 60, attribution: "Synthetic", reason: null },
    { id: "roadwork", ready: true, jurisdictions: ["WA test"], refresh_seconds: 60, attribution: "Synthetic", reason: "Partial coverage" },
    { id: "route", ready: false, jurisdictions: ["Synthetic"], refresh_seconds: null, attribution: "Synthetic", reason: "Synthetic route credentials unavailable" },
  ],
};

async function mockMetadata(page: Page, failReferenceOnce = false) {
  let referenceCalls = 0;
  await page.route("**/api/operations/reference", async (route) => {
    referenceCalls += 1;
    if (failReferenceOnce && referenceCalls === 1) return route.fulfill({ status: 503, json: { error: "Synthetic reference outage" } });
    return route.fulfill({ json: reference });
  });
  await page.route("**/api/verified/coverage", (route) => route.fulfill({ status: 503, json: {
    available: false, reason: "Synthetic test-only directory unavailable.", dataset: null, generated_at: null, coverage: null,
  } }));
  await page.route("**/api/outcomes/status", (route) => route.fulfill({ status: 503, json: {
    status: "unavailable", reason: "Synthetic test-only: no approved actual-history model.", model_version: null,
    support: null, evaluation: null, limitations: ["No synthetic prediction is shown."],
  } }));
  return () => referenceCalls;
}

async function fillWorksite(page: Page) {
  await page.getByLabel("Worksite label").fill("Synthetic Seattle yard");
  await page.getByLabel("Latitude", { exact: true }).fill(String(point.lat));
  await page.getByLabel("Longitude", { exact: true }).fill(String(point.lon));
  await page.getByLabel("Annual AEF year").selectOption("2025");
}

test("real backend readiness renders at desktop and mobile without a site request", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/operations");
  await expect(page.getByRole("heading", { name: "Plan one mobilization" })).toBeVisible();
  await page.locator("summary").filter({ hasText: "Truck route" }).click();
  await expect(page.getByText("Local time zone: America/New_York").first()).toBeVisible();
  const readiness = page.getByRole("region", { name: "Provider readiness" });
  await expect(readiness.getByText("Checking…")).toHaveCount(0);
  await expect(readiness.getByText("3,413 utilities · 2024 EIA vintage")).toBeVisible();
  await expect(readiness.getByText(/Separate LVR provisioning required/)).toBeVisible();
  await expect(readiness.getByText(/No current, externally approved model/)).toBeVisible();
  await page.locator("summary").filter({ hasText: "Truck route" }).click();
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath("operations-real-backend-initial-1440.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client);
  await page.screenshot({ path: testInfo.outputPath("operations-real-backend-initial-390.png"), fullPage: true });
  expect(errors.filter((error) => /hydration|did not match|uncaught/i.test(error))).toEqual([]);
});

test("mixed provider states stay bound to the submitted worksite without hydration errors", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  await mockMetadata(page);
  await page.route("**/api/operations/site?*", async (route) => route.fulfill({ json: {
    request: { ...point, year: 2025 }, weather, roadwork,
    soil: emptyEnvelope("soil", "unavailable", "Synthetic test-only soil unavailable."),
    aef: emptyEnvelope("aef", "unavailable", "Synthetic test-only AEF point/year unavailable."),
  } }));
  await page.goto("/operations");
  await page.locator("summary").filter({ hasText: "Truck route" }).click();
  await page.locator("summary").filter({ hasText: "Construction duration evidence" }).click();
  await expect(page.getByText("Local time zone: America/New_York").first()).toBeVisible();
  await fillWorksite(page);
  await page.getByRole("button", { name: "Check worksite" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Synthetic Seattle yard" })).toBeVisible();
  await expect(page.getByText("Synthetic test-only clouds")).toBeVisible();
  await expect(page.getByRole("paragraph").filter({ hasText: "outside supported road-work coverage" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Evaluate actual-outcome cohort" })).toBeDisabled();
  await expect(page.getByText(/No numerical estimate/)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Refresh cooling down" })).toBeDisabled();
  expect(errors.filter((error) => /hydration|did not match|uncaught/i.test(error))).toEqual([]);
  await page.locator("summary").filter({ hasText: "Truck route" }).click();
  await page.locator("summary").filter({ hasText: "Construction duration evidence" }).click();
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath("mocked-operations-1440.png"), fullPage: true });
});

test("stale responses cannot replace evidence and polling stops while hidden or unmounted", async ({ page }) => {
  await page.clock.install({ time: new Date(stamp) });
  await mockMetadata(page);
  let siteCalls = 0;
  let releaseFirstSite!: () => void;
  let markFirstSiteStarted!: () => void;
  const firstSiteStarted = new Promise<void>((resolve) => { markFirstSiteStarted = resolve; });
  const firstSiteRelease = new Promise<void>((resolve) => { releaseFirstSite = resolve; });
  await page.route("**/api/operations/site?*", async (route) => {
    siteCalls += 1;
    const url = new URL(route.request().url());
    const requestPoint = { lat: Number(url.searchParams.get("lat")), lon: Number(url.searchParams.get("lon")) };
    if (siteCalls === 1) { markFirstSiteStarted(); await firstSiteRelease; }
    const boundWeather = { ...weather, data: { ...weather.data, samples: [{ ...weather.data.samples[0], point: requestPoint }] } };
    await route.fulfill({ json: { request: { ...requestPoint, year: 2025 }, weather: boundWeather, roadwork,
      soil: emptyEnvelope("soil", "unavailable", "Synthetic test-only soil unavailable."),
      aef: emptyEnvelope("aef", "unavailable", "Synthetic test-only AEF unavailable.") } });
  });
  let conditionCalls = 0;
  let releaseFirstCondition!: () => void;
  let markFirstConditionStarted!: () => void;
  const firstConditionStarted = new Promise<void>((resolve) => { markFirstConditionStarted = resolve; });
  const firstConditionRelease = new Promise<void>((resolve) => { releaseFirstCondition = resolve; });
  await page.route("**/api/operations/conditions?*", async (route) => {
    conditionCalls += 1;
    const url = new URL(route.request().url());
    const requestPoint = { lat: Number(url.searchParams.get("lat")), lon: Number(url.searchParams.get("lon")) };
    if (conditionCalls === 1) { markFirstConditionStarted(); await firstConditionRelease; }
    const description = conditionCalls === 1 ? "Synthetic stale response must not render" : "Synthetic visible poll response";
    const boundWeather = { ...weather, data: { ...weather.data, samples: [{ ...weather.data.samples[0], point: requestPoint,
      forecast: [{ ...weather.data.samples[0].forecast[0], description }] }] } };
    await route.fulfill({ json: { request: requestPoint, weather: boundWeather, roadwork } });
  });
  await page.goto("/operations");
  await fillWorksite(page);
  await page.getByRole("button", { name: "Check worksite" }).click();
  await firstSiteStarted;
  await page.getByLabel("Latitude", { exact: true }).fill("47.7");
  releaseFirstSite();
  await expect(page.getByRole("heading", { name: "No active worksite" })).toBeVisible();

  await page.getByLabel("Latitude", { exact: true }).fill(String(point.lat));
  await page.getByRole("button", { name: "Check worksite" }).click();
  await expect(page.locator("main").getByRole("alert").filter({ hasText: "including failed checks" })).toBeVisible();
  expect(siteCalls).toBe(1);
  await page.clock.fastForward(60_100);
  await page.getByRole("button", { name: "Check worksite" }).click();
  await expect(page.getByRole("heading", { name: "Synthetic Seattle yard" })).toBeVisible();
  await page.clock.fastForward(60_100);
  await firstConditionStarted;
  await page.getByLabel("Longitude", { exact: true }).fill("-122.4");
  releaseFirstCondition();
  await expect(page.getByText("Synthetic stale response must not render")).toHaveCount(0);

  await page.getByLabel("Longitude", { exact: true }).fill(String(point.lon));
  await page.getByRole("button", { name: "Check worksite" }).click();
  await expect(page.getByText(/Existing soil and annual evidence was reused/)).toBeVisible();
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }); document.dispatchEvent(new Event("visibilitychange")); });
  await page.clock.fastForward(120_000);
  expect(conditionCalls).toBe(1);
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" }); document.dispatchEvent(new Event("visibilitychange")); });
  await page.clock.fastForward(60_100);
  await expect.poll(() => conditionCalls).toBe(2);
  await expect(page.getByText("Synthetic visible poll response")).toBeVisible();
  await page.goto("/");
  await page.clock.fastForward(120_000);
  expect(conditionCalls).toBe(2);
});

test("readiness can retry and bounds errors are field-friendly", async ({ page }) => {
  const referenceCalls = await mockMetadata(page, true);
  await page.goto("/operations");
  await expect(page.getByText("Synthetic reference outage").first()).toBeVisible();
  await page.getByRole("button", { name: "Retry readiness checks" }).click();
  await expect(page.getByText("Refresh 60s while visible")).toBeVisible();
  expect(referenceCalls()).toBe(2);
  await page.getByLabel("Worksite label").fill("Invalid point");
  await page.getByLabel("Latitude", { exact: true }).fill("91");
  await page.getByLabel("Longitude", { exact: true }).fill("-122.3");
  await page.getByLabel("Annual AEF year").selectOption("2025");
  await page.getByRole("button", { name: "Check worksite" }).click();
  const alert = page.locator("main").getByRole("alert").filter({ hasText: "Latitude:" });
  await expect(alert).toContainText("Latitude:");
  await expect(alert).not.toContainText('"code"');
});

test("map click with year selected calls the site API for the clicked point", async ({ page }) => {
  await mockMetadata(page);
  let siteUrl = "";
  await page.route("**/api/operations/site?*", async (route) => {
    siteUrl = route.request().url();
    const url = new URL(siteUrl);
    const requestPoint = { lat: Number(url.searchParams.get("lat")), lon: Number(url.searchParams.get("lon")) };
    const boundWeather = { ...weather, data: { ...weather.data, samples: [{ ...weather.data.samples[0], point: requestPoint }] } };
    await route.fulfill({ json: {
      request: { ...requestPoint, year: 2025 }, weather: boundWeather, roadwork,
      soil: {
        ...emptyEnvelope("soil", "available", "Synthetic soil with horizon pH."),
        evidence_hash: "c".repeat(64),
        coverage: { requested: 1, completed: 1, failed: 0, truncated: false },
        data: {
          scope: "Synthetic soil horizons.",
          map_units: [{ mukey: "1", name: "Synthetic unit", area_symbol: "WA001", survey_updated_at: null, components: [{
            cokey: "2", name: "Synthetic component", percent: 100, drainage_class: "Well drained", hydrologic_group: "B",
            horizons: [{ chkey: "h1", depth_top_cm: 0, depth_bottom_cm: 15, ph_h2o_1_to_1: 6.4, ph_method: "1:1 soil-water", depth_unit: "cm" }],
          }] }],
        },
      },
      aef: emptyEnvelope("aef", "unavailable", "Synthetic test-only AEF unavailable."),
    } });
  });
  await page.goto("/operations?year=2025");
  await expect(page.getByLabel("Annual AEF year")).toHaveValue("2025");
  const map = page.getByRole("application", { name: "Click the map to set the worksite coordinates" });
  await expect(map).toHaveAttribute("data-ready", "true", { timeout: 30_000 });
  // MapLibre map.fire("click") requires originalEvent.target (_onMapClick). Drive the same
  // worksite pick callback the real click handler uses, at a fixed CONUS point.
  const fired = await map.evaluate((node) => {
    const host = node as HTMLDivElement & { __worksitePick?: (point: { lat: number; lon: number }) => void };
    if (!host.__worksitePick) return false;
    host.__worksitePick({ lat: 47.6062, lon: -122.3321 });
    return true;
  });
  expect(fired).toBe(true);
  await expect(page.getByRole("heading", { name: "Map-selected worksite" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("pH 6.4")).toBeVisible();
  await expect(page.getByText(/depth 0-15 cm/)).toBeVisible();
  const called = new URL(siteUrl);
  expect(called.searchParams.get("year")).toBe("2025");
  expect(called.searchParams.get("lat")).toBe("47.6062");
  expect(called.searchParams.get("lon")).toBe("-122.3321");
});

test("mobile layout keeps the worksite form before the evidence board and does not overflow", async ({ page }, testInfo: TestInfo) => {
  await mockMetadata(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/operations");
  const order = await page.locator("main").evaluate((main) => {
    const form = main.querySelector("input[required]");
    const blank = [...main.querySelectorAll("h3")].find((node) => node.textContent?.includes("Start with a confirmed point"));
    return form && blank ? Boolean(form.compareDocumentPosition(blank) & Node.DOCUMENT_POSITION_FOLLOWING) : false;
  });
  expect(order).toBe(true);
  const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client);
  await page.screenshot({ path: testInfo.outputPath("mocked-operations-390.png"), fullPage: true });
});
