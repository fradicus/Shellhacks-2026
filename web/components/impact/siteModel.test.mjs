import assert from "node:assert/strict";
import { test } from "node:test";
import { evidenceLines, soilPhSummary, WaterSchema } from "./siteModel.ts";

const horizon = (top, bottom, ph) => ({ depth_top_cm: top, depth_bottom_cm: bottom, ph_h2o_1_to_1: ph });
const soil = (components) => ({ map_units: [{ name: "unit", components }] });
const component = (percent, horizons) => ({ name: "C", percent, drainage_class: null, hydrologic_group: null, horizons });

test("pH is component % × thickness weighted over 0–30 cm; missing pH or percent is skipped, never zero", () => {
  // A: 20 cm × 60 @ 5.0 + 10 cm × 60 @ 6.0; B: 30 cm × 40 @ 7.0; C has no percent → (6000 + 3600 + 8400) / 3000 = 6.0
  const data = soil([component(60, [horizon(0, 20, 5), horizon(20, 80, 6)]), component(40, [horizon(0, 30, 7)]), component(null, [horizon(0, 30, 3)])]);
  assert.deepEqual(soilPhSummary(data), { value: 6, horizonsUsed: 3 });
  assert.deepEqual(soilPhSummary(soil([component(100, [horizon(0, 30, null)])])), { value: null, horizonsUsed: 0 });
  assert.deepEqual(soilPhSummary(soil([component(100, [horizon(40, 80, 5)])])), { value: null, horizonsUsed: 0 });
  assert.equal(soilPhSummary(null).value, null);
});

test("no FEMA polygon reads as unknown, never Zone X; unavailable layers add no claim", () => {
  const water = { status: "partial", limitations: [], retrieved_at: "2026-09-27T12:00:00Z", data: { rivers: null, tides: null, flood: { zones: [] }, wetlands: null } };
  assert.equal(WaterSchema.safeParse({ water }).success, true);
  const lines = evidenceLines(null, water);
  assert.deepEqual(lines, ["FEMA flood zone unknown (no mapped polygon)"]);
  assert.equal(lines.some((line) => /Zone X/.test(line)), false);
  assert.deepEqual(evidenceLines(null, { ...water, data: null }), []);
});
