import { expect, test } from "@playwright/test";
import type { NationalExplorerPayload } from "../../lib/national/types";

for (const width of [1440, 390]) {
  test(`national evidence loads only on selection at ${width}px`, async ({ page, request }, testInfo) => {
    const response = await request.get("/api/national?limit=1");
    expect(response.ok()).toBeTruthy();
    const payload = await response.json() as NationalExplorerPayload;
    const project = payload.mapProjects.find(p => !p._id.startsWith("legacy:") && p.center
      && ["confirmed", "unreviewed"].includes(p.location_review) && p.status_group !== "in_service");
    test.skip(!project, "This dataset has no planned national points; run against a published national dataset.");
    let details = 0;
    page.on("request", req => { if (new URL(req.url()).pathname === "/api/national/project") details++; });
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/time");
    await expect(page.getByRole("button", { name: "3D", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("Raising the time axis…", { exact: true })).toBeHidden({ timeout: 30_000 });
    await page.screenshot({ path: testInfo.outputPath("overview.png") });
    expect(details).toBe(0);
    await page.getByRole("button", { name: /^Projects/ }).click();
    await page.getByLabel("Filter projects by name or ID").fill(project!._id);
    const detailResponse = page.waitForResponse(res => new URL(res.url()).pathname === "/api/national/project");
    await page.locator("#all-projects li button").filter({ hasText: project!._id }).click();
    const detail = await (await detailResponse).json();
    expect(detail.project._id).toBe(project!._id);
    const card = page.getByRole("complementary", { name: "Selected project" });
    await expect(card).toContainText(project!.native_id);
    await expect(card).toContainText("National discovery point");
    await expect(card).toContainText(detail.dataset);
    expect(details).toBe(1);
    await page.screenshot({ path: testInfo.outputPath("selected-3d.png") });
    await page.getByRole("button", { name: "2D", exact: true }).click();
    await expect(page.getByRole("button", { name: "2D", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect(card).toContainText(project!.native_id);
    await page.screenshot({ path: testInfo.outputPath("selected-2d.png") });
    await page.getByRole("button", { name: "3D", exact: true }).click();
    expect(details).toBe(1);
  });
}
