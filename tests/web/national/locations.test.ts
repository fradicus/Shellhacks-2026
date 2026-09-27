import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { displayPoints, locationLabel } from "../../../web/lib/national/locations.ts";
import type { NationalProject } from "../../../web/lib/national/types.ts";

const projects: NationalProject[] = JSON.parse(readFileSync(new URL("../../../data/texas/statewide/projects.json", import.meta.url), "utf8"));

test("Texas display keeps 635 tentative and 1218 county projects, without changing exact centers", () => {
  const before = JSON.stringify(projects);
  const mapped = projects.filter((p) => displayPoints(p).length);
  assert.equal(mapped.length, 1853);
  assert.equal(mapped.filter((p) => p.center).length, 635);
  const county = mapped.filter((p) => !p.center);
  assert.equal(county.length, 1218);
  assert.equal(county.flatMap(displayPoints).length, 1407);
  assert.ok(county.every((p) => locationLabel(p).includes("exact site unknown")));
  assert.ok(mapped.filter((p) => p.center).every((p) => locationLabel(p) === "Tentative location"));
  assert.equal(JSON.stringify(projects), before);
});

test("county anchors keep all named counties and reject malformed or unsupported references", () => {
  const county = projects.find((p) => (p.approximate_location?.anchors.length ?? 0) > 1)!;
  assert.equal(displayPoints(county).length, county.approximate_location!.anchors.length);
  assert.deepEqual(displayPoints({ ...county, location_review: "rejected" }), []);
  assert.deepEqual(displayPoints({ ...county, approximate_location: undefined }), []);
  const altered = structuredClone(county);
  altered.approximate_location!.anchors = [{ ...altered.approximate_location!.anchors[0], lat: NaN }];
  assert.deepEqual(displayPoints(altered), []);
  altered.approximate_location!.anchors = [{ ...county.approximate_location!.anchors[0], county_geoid: "99999" }];
  assert.deepEqual(displayPoints(altered), []);
});
