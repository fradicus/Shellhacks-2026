import { expect, test } from "@playwright/test";

test("state and county cascade stays in the URL and clears stale descendants", async ({ page }, testInfo) => {
  await page.goto("/explore");
  await expect(page.getByRole("heading", { name: "Transmission project explorer" })).toBeVisible();
  await page.getByLabel("Census region").selectOption("1");
  await expect(page).toHaveURL(/region=1/);
  await page.getByLabel("State or territory").selectOption("25");
  await expect(page).toHaveURL(/state=25/);
  await page.getByLabel("County or equivalent").selectOption("25001");
  await expect(page).toHaveURL(/county=25001/);
  await page.getByLabel("Census region").selectOption("3");
  await expect(page).toHaveURL(/region=3/);
  await expect(page).not.toHaveURL(/state=25|county=25001/);
  await expect(page.getByLabel("County or equivalent")).toBeDisabled();
  await page.screenshot({ path: testInfo.outputPath("explore-desktop.png"), fullPage: true });
});

test("text state restores with browser Back and empty differs from invalid URL", async ({ page }) => {
  await page.goto("/explore");
  const text = page.getByLabel("Project text");
  await text.fill("zzzz-test-no-national-project");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByText("No matches in the imported records")).toBeVisible();
  await page.getByRole("button", { name: "Reset" }).click();
  await expect(page).toHaveURL(/\/explore$/);
  await expect(page.getByLabel("Project text")).toHaveValue("");
  await expect(page.locator("section[aria-label='Filtered project counts'] strong").first()).toHaveText("1,286");
  await page.goBack();
  await expect(page).toHaveURL(/text=zzzz-test-no-national-project/);
  await expect(page.getByLabel("Project text")).toHaveValue("zzzz-test-no-national-project");
  await expect(page.getByText("No matches in the imported records")).toBeVisible();

  await page.goto("/explore?from=2029-01-01&to=2028-01-01");
  await expect(page.getByText(/Invalid explorer URL/)).toBeVisible();
  await expect(page.getByText("Project records are unavailable")).toBeVisible();
});

test("mobile explorer has no document-level horizontal overflow", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explore");
  const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client);
  await expect(page.getByRole("heading", { name: "Transmission project explorer" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("explore-mobile.png"), fullPage: true });
});

test("mind map tab is reachable from explorer URL state", async ({ page }) => {
  await page.goto("/explore?view=mindmap");
  await expect(page.getByRole("tab", { name: "Mind map" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: /Region circle → state → place → electrical/i })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByLabel("Mind map charts")).toBeVisible();
  await page.getByRole("tab", { name: "Map & list" }).click();
  await expect(page).not.toHaveURL(/view=mindmap/);
});

test("API rejects duplicate parameters and its exact counts drive the page", async ({ page, request }) => {
  const duplicate = await request.get("/api/national?state=25&state=13");
  expect(duplicate.status()).toBe(400);

  const response = await request.get("/api/national?state=25&limit=25");
  expect(response.status()).toBe(200);
  const payload = await response.json();
  expect(payload.total).toBeGreaterThanOrEqual(0);
  expect(payload.locatedTotal + (payload.approximateTotal ?? 0) + payload.unlocatedTotal).toBe(payload.total);
  expect(payload.mapProjects.length).toBe(payload.locatedTotal + (payload.approximateTotal ?? 0));

  await page.goto("/explore?state=25&limit=25");
  await expect(page.locator("section[aria-label='Filtered project counts'] strong").first()).toHaveText(payload.total.toLocaleString("en-US"));
});
