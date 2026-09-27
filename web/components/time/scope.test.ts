import assert from "node:assert/strict";
import test from "node:test";
import { formatScope, haversineMi, inScope, parseScope, planOf, statesOf } from "./scope";
import type { TimeProject } from "./TimeView";
import type { NationalProject } from "../../lib/national/types";

// Explicit test-only records; no synthetic data enters the application.
const legacy = (source_id: string, lat = 33, lon = -82): TimeProject => ({
  key: `k-${source_id}`, name: "Test", utility: "unknown", owner_code: null, center: { lat, lon },
  in_service: { date: null, precision: "unknown", raw: null }, confidence: null, source_id, page: null,
});
const national = (states: string[], planning_region: string | null): TimeProject => ({
  ...legacy("test-source"),
  national: { tier: "tentative", project: { states, planning_region } as NationalProject },
});
const regionOf = new Map([["48", "3"], ["22", "3"], ["36", "1"]]);

test("parse and format round-trip, and malformed values are ignored", () => {
  for (const raw of ["region:3", "state:48", "plan:ercot", "pin:29.7604,-95.3698"])
    assert.equal(formatScope(parseScope(raw)!), raw);
  for (const raw of [null, "", "region:5", "state:4", "plan:ER COT", "pin:,", "pin:91,0", "pin:1,2,3", "pin:a,b", "county:01"])
    assert.equal(parseScope(raw), null, String(raw));
});

test("haversine matches the pipeline matcher", () => {
  // pipeline/matches/core.py haversine_mi(29.7604, -95.3698, 30.2672, -97.7431)
  assert.ok(Math.abs(haversineMi(29.7604, -95.3698, 30.2672, -97.7431) - 146.2426685354375) < 1e-9);
});

test("pin holds centres within 25 statute miles, inclusive, and never an unlocated project", () => {
  const pin = { kind: "pin" as const, lat: 33, lon: -82 };
  const deg = (mi: number) => mi / ((Math.PI / 180) * 3958.8);
  assert.ok(inScope(legacy("desc-2025", 33 + deg(24.99)), pin, regionOf));
  assert.ok(!inScope(legacy("desc-2025", 33 + deg(25.01)), pin, regionOf));
  assert.ok(!inScope({ ...legacy("desc-2025"), center: null }, pin, regionOf));
});

test("state and region come from stored states or the legacy filing", () => {
  assert.deepEqual(statesOf(legacy("desc-2024")), ["45"]);
  assert.deepEqual(statesOf(legacy("gpc-2025")), ["13"]);
  assert.deepEqual(statesOf(legacy("sample")), []);
  const line = national(["48", "22"], "PJM");
  assert.ok(inScope(line, { kind: "state", code: "22" }, regionOf));
  assert.ok(inScope(line, { kind: "region", code: "3" }, regionOf));
  assert.ok(!inScope(line, { kind: "region", code: "1" }, regionOf));
  assert.equal(planOf(line), "pjm");
  assert.ok(inScope(line, { kind: "plan", code: "pjm" }, regionOf));
  assert.equal(planOf(national([], null)), null);
});
