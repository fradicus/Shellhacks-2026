import { expect, test } from "@playwright/test";
import type { CandidatePage } from "../../lib/national-pairs/types";

for (const width of [1440, 390]) {
  test(`national candidates, paging, scope and shared selection at ${width}px`, async ({ page, request }, testInfo) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width, height: 900 });
    let evidence = 0;
    page.on("request", (r) => { if (new URL(r.url()).pathname === "/api/national/project") evidence++; });
    const response = page.waitForResponse(r => new URL(r.url()).pathname === "/api/national-pairs");
    await page.goto("/time");
    const first = await (await response).json() as CandidatePage;
    expect(first.available).toBe(true);
    expect(first.pairs).toHaveLength(50);
    const list = page.getByRole("navigation", { name: "Overlap pairs" });
    await expect(list.locator("ol li")).toHaveCount(50);
    expect(evidence).toBe(0);
    await list.getByRole("button", { name: "Load more candidates" }).click();
    await expect(list.locator("ol li")).toHaveCount(100);
    await expect(page.getByText("Raising the time axis…", { exact: true })).toBeHidden({ timeout: 45_000 });
    await list.locator("ol li button").nth(55).click();
    const card = page.getByRole("complementary", { name: "Selected pair" });
    await expect(card).toContainText("Provisional candidate");
    await expect(card).toContainText("miles by road");
    expect(evidence).toBe(0);
    const shared = page.url();
    await card.locator("summary").first().click();
    await expect(card).toContainText("National discovery point");
    expect(evidence).toBe(1);
    await page.screenshot({ path: testInfo.outputPath("candidate-selected.png") });
    await page.goto(shared);
    await expect(card).toContainText("Provisional candidate", { timeout: 45_000 });
    await page.getByRole("button", { name: "Close pair", exact: true }).click();
    await page.getByRole("button", { name: "2D", exact: true }).click();
    await expect(page.getByRole("button", { name: "2D", exact: true })).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "3D", exact: true }).click();
    await page.getByRole("button", { name: /^Scope:/ }).click();
    await page.getByRole("combobox").fill("Texas");
    const scopedResponse = page.waitForResponse(r => new URL(r.url()).pathname === "/api/national-pairs" && new URL(r.url()).searchParams.get("scope") === "state:48");
    await page.getByRole("option").filter({ hasText: "Texas" }).click();
    const scoped = await (await scopedResponse).json() as CandidatePage;
    expect(scoped.total).toBeGreaterThan(50);
    expect(scoped.total).toBeLessThan(first.total);
    await expect(list.locator("ol li")).toHaveCount(50);
    await expect(list).toContainText("Texas");
    await expect(page).toHaveURL(/scope=state%3A48/);
    const pin = await request.get(`/api/national-pairs?dataset=${encodeURIComponent(first.dataset)}&scope=pin:29.5,-95.5`);
    expect(pin.ok()).toBe(true);
    await page.screenshot({ path: testInfo.outputPath("texas-candidates.png") });
    await list.getByRole("button", { name: "Legacy pairs", exact: true }).click();
    await expect(list.getByRole("group", { name: "Which pairs" })).toBeVisible();
  });
}

test("candidate failure is explicit and retry restores the list", async ({ page }) => {
  let fail = true;
  await page.route("**/api/national-pairs?**", route => fail
    ? route.fulfill({ status: 503, json: { available: false, reason: "Candidate publication unavailable." } })
    : route.continue());
  await page.goto("/time");
  await expect(page.getByRole("navigation", { name: "Overlap pairs" }).getByRole("alert")).toContainText("Candidate publication unavailable.");
  fail = false;
  await page.getByRole("button", { name: "Retry candidates" }).click();
  await expect(page.getByRole("navigation", { name: "Overlap pairs" }).locator("ol li")).toHaveCount(50);
});

test("a late nationwide response cannot replace a narrower scope", async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let intercepted!: () => void;
  const started = new Promise<void>(resolve => { intercepted = resolve; });
  await page.route("**/api/national-pairs?**", async route => {
    if (new URL(route.request().url()).searchParams.has("scope")) return route.continue();
    const response = await route.fetch();
    intercepted();
    await held;
    await route.fulfill({ response }).catch(() => {}); // Browser may already have aborted this request.
  });
  await page.goto("/time");
  await started;
  await page.getByRole("button", { name: /^Scope:/ }).click();
  await page.getByRole("combobox").fill("Texas");
  await page.getByRole("option").filter({ hasText: "Texas" }).click();
  const list = page.getByRole("navigation", { name: "Overlap pairs" });
  await expect(list.locator("ol li")).toHaveCount(50);
  await expect(list).toContainText("Texas");
  const text = await list.innerText();
  release();
  await page.waitForTimeout(300);
  expect(await list.innerText()).toBe(text);
});

test("a changed dataset asks for refresh instead of showing an empty result", async ({ page }) => {
  await page.route("**/api/national-pairs?**", route => route.fulfill({ status: 409,
    json: { available: false, reason: "Dataset changed. Refresh the page." } }));
  await page.goto("/time");
  await expect(page.getByRole("button", { name: "Refresh page", exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Overlap pairs" })).not.toContainText("No candidates");
});

for (const width of [1440, 390]) {
  test(`submitted search, identities and shared query at ${width}px`, async ({ page, request }, testInfo) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width, height: 900 });
    let searches = 0;
    page.on("request", r => { if (new URL(r.url()).pathname === "/api/national-pairs" && new URL(r.url()).searchParams.has("q")) searches++; });
    const initial = page.waitForResponse(r => new URL(r.url()).pathname === "/api/national-pairs");
    await page.goto("/time");
    const first = await (await initial).json() as CandidatePage;
    const later = await (await request.get(`/api/national-pairs?dataset=${first.dataset}&offset=50`)).json() as CandidatePage;
    const target = later.projects.find(p => p._id === later.pairs[5].a)!;
    const list = page.getByRole("navigation", { name: "Overlap pairs" });
    const input = list.getByRole("searchbox");
    await expect(list.locator("ol li")).toHaveCount(50);
    await input.fill(target._id);
    expect(searches).toBe(0);
    const searched = page.waitForResponse(r => new URL(r.url()).searchParams.get("q") === target._id);
    await input.press("Enter");
    const found = await (await searched).json() as CandidatePage;
    expect(found.available).toBe(true);
    expect(found.total).toBeGreaterThan(0);
    await expect(list.locator("ol li")).toHaveCount(found.pairs.length);
    await expect(list).toContainText(target.owner ?? "Owner unknown");
    await expect(list).toContainText(target.source_id);
    await expect(list).toContainText(target.native_id);
    expect(new URL(page.url()).searchParams.get("q")).toBe(target._id);
    const listBox = await list.locator("ol").boundingBox();
    expect(listBox!.height).toBeGreaterThan(140);
    await page.screenshot({ path: testInfo.outputPath("candidate-search.png") });
    await expect(page.getByText("Raising the time axis…", { exact: true })).toBeHidden({ timeout: 45_000 });
    await list.locator("ol li button").first().click();
    const shared = page.url();
    expect(new URL(shared).searchParams.has("pair")).toBe(true);
    await page.goto(shared);
    await expect(input).toHaveValue(target._id);
    await expect(page.getByRole("complementary", { name: "Selected pair" })).toContainText("Provisional candidate", { timeout: 45_000 });
    await page.getByRole("button", { name: "Close pair", exact: true }).click();
    await input.fill("Oncor");
    await input.press("Enter");
    await page.getByRole("button", { name: /^Scope:/ }).click();
    await page.getByRole("combobox").fill("Texas");
    const scoped = page.waitForResponse(r => {
      const q = new URL(r.url()).searchParams;
      return q.get("scope") === "state:48" && q.get("q") === "Oncor";
    });
    await page.getByRole("option").filter({ hasText: "Texas" }).click();
    expect(((await (await scoped).json()) as CandidatePage).total).toBeGreaterThan(50);
    await expect(list).toContainText("matches for “Oncor” · Texas");
    await input.fill("no-matching-project-987654321");
    await input.press("Enter");
    await expect(list).toContainText("No candidates match");
    await expect(list.locator("ol li")).toHaveCount(0);
    await list.getByRole("button", { name: "Clear", exact: true }).click();
    await expect(input).toHaveValue("");
    await expect(list.locator("ol li")).toHaveCount(50);
    expect(new URL(page.url()).searchParams.has("q")).toBe(false);
  });
}

test("a late search cannot replace a newer submitted query", async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let intercepted!: () => void;
  const started = new Promise<void>(resolve => { intercepted = resolve; });
  await page.route("**/api/national-pairs?**", async route => {
    if (new URL(route.request().url()).searchParams.get("q") !== "Oncor") return route.continue();
    const response = await route.fetch();
    intercepted();
    await held;
    await route.fulfill({ response }).catch(() => {});
  });
  await page.goto("/time");
  const list = page.getByRole("navigation", { name: "Overlap pairs" });
  const input = list.getByRole("searchbox");
  await input.fill("Oncor");
  await input.press("Enter");
  await started;
  await input.fill("no-matching-project-987654321");
  await input.press("Enter");
  await expect(list).toContainText("No candidates match");
  release();
  await page.waitForTimeout(300);
  await expect(list.locator("ol li")).toHaveCount(0);
  await expect(list).toContainText("no-matching-project-987654321");
});
