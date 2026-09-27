import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { projectSummary } from "../../../web/lib/national/summaries.ts";
import { displayPoints, locationLabel } from "../../../web/lib/national/locations.ts";
import type { NationalProject } from "../../../web/lib/national/types.ts";

test("summaries preserve real project geometry, labels and milestones while omitting evidence", () => {
  const projects: NationalProject[] = JSON.parse(readFileSync(new URL("../../../data/texas/statewide/projects.json", import.meta.url), "utf8"));
  const before = JSON.stringify(projects);
  const summaries = projects.map(projectSummary);
  for (let i = 0; i < projects.length; i++) {
    const full = projects[i], summary = summaries[i];
    assert.equal(summary._id, full._id);
    assert.deepEqual(summary.in_service, full.in_service);
    assert.equal(summary.status_group, full.status_group);
    assert.equal(summary.location_candidate?.tier, full.location_candidate?.tier);
    assert.equal(locationLabel(summary), locationLabel(full));
    const coords = (p: Parameters<typeof displayPoints>[0]) => displayPoints(p).map(({ lat, lon }) => [lat, lon]);
    assert.deepEqual(coords(summary), coords(full));
    assert.equal("raw" in summary.evidence, false);
    assert.equal("location_verification" in summary, false);
    assert.equal("description" in summary, false);
    assert.equal("endpoints" in (summary.location_candidate ?? {}), false);
    assert.equal("evidence" in (summary.center ?? {}), false);
  }
  assert.equal(JSON.stringify(projects), before);
  assert.ok(JSON.stringify(summaries).length < before.length);
});
