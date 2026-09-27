import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { buildMindMapTree } from "../../../web/lib/national/mindmap.ts";
import { parseNationalFilters, serializeNationalFilters } from "../../../web/lib/national/filters.ts";
import type { NationalGeography, NationalProject } from "../../../web/lib/national/types.ts";

const geography = {
  schema_version: "national-geography-v1",
  authority: "U.S. Census Bureau",
  provenance: { sources: [], notes: [] },
  counts: {},
  regions: [
    { region_code: "1", name: "Northeast", bounds: null },
    { region_code: "3", name: "South", bounds: null },
  ],
  divisions: [],
  states: [
    { state_fips: "25", usps: "MA", name: "Massachusetts", scope: "state", selectable_primary: true, census_region_code: "1", census_division_code: "1", bounds: null },
    { state_fips: "13", usps: "GA", name: "Georgia", scope: "state", selectable_primary: true, census_region_code: "3", census_division_code: "5", bounds: null },
  ],
  counties: [
    { county_geoid: "25017", state_fips: "25", county_fips: "017", name: "Middlesex", full_name: "Middlesex County", state_usps: "MA", state_name: "Massachusetts", scope: "state", selectable_primary: true, bounds: null },
  ],
} satisfies NationalGeography;

const project = (overrides: Partial<NationalProject>): NationalProject => ({
  _id: "test-only:one",
  source_id: "test-only-source",
  native_id: "T-1",
  name: "Harbor reinforcement",
  owner: "Test Utility",
  other_owners: [],
  planning_region: "TEST",
  states: ["25"],
  counties: ["25017"],
  geography_basis: "test fixture",
  status: "Planned",
  status_group: "planned",
  in_service: { raw: "2028", value: "2028", precision: "year" },
  center: null,
  location_review: "unlocated",
  evidence: { page: null, sheet: "Test", row: 2, raw: { clearly: "test-only" } },
  ...overrides,
});

test("mind map nests region circle → state → place → electrical without inventing cities", () => {
  const tree = buildMindMapTree([
    project({}),
    project({
      _id: "test-only:two",
      native_id: "T-2",
      name: "Substation breaker work",
      states: ["13"],
      counties: [],
      status_group: "under_construction",
      owner: "Southern Test",
    }),
    project({
      _id: "test-only:three",
      native_id: "T-3",
      name: "Unlocated feeder",
      states: [],
      counties: [],
      status_group: "unknown",
      owner: null,
    }),
  ], geography);

  assert.equal(tree.meta.included, 3);
  assert.equal(tree.regions.length, 3);
  const northeast = tree.regions.find((region) => region.code === "1");
  assert.ok(northeast);
  assert.equal(northeast.states[0]?.name, "Massachusetts");
  assert.equal(northeast.states[0]?.places[0]?.label, "Middlesex County");
  assert.equal(northeast.states[0]?.places[0]?.kind, "county");
  assert.equal(northeast.states[0]?.places[0]?.projects[0]?.name, "Harbor reinforcement");

  const unknown = tree.regions.find((region) => region.code === "unknown");
  assert.ok(unknown);
  assert.equal(unknown.states[0]?.places[0]?.label, "Unknown place");
  assert.deepEqual(
    tree.charts.byStatus.map((slice) => slice.key).sort(),
    ["planned", "under_construction", "unknown"],
  );
});

test("mind map prefers reviewed facility names for place labels", () => {
  const tree = buildMindMapTree([
    project({
      location_verification: {
        project_id: "test-only:one",
        project_facts_sha256: "abc",
        producer: "test",
        location_kind: "site",
        points: [{
          role: "site",
          facility_id: "fac-1",
          facility_name: "Sandy Pond",
          lat: 42.5,
          lon: -71.5,
          original_geometry: { crs: "EPSG:4326", type: "Point", coordinates: [-71.5, 42.5], transform: "none" },
          precision: null,
          uncertainty_m: null,
          geometry_evidence: [],
          identity_evidence: [],
          identity_rationale: "test",
        }],
        reviews: [],
        events: [],
      },
      center: { lat: 42.5, lon: -71.5, basis: "one", evidence: "test" },
      location_review: "confirmed",
    }),
  ], geography);
  assert.equal(tree.regions[0]?.states[0]?.places[0]?.kind, "facility");
  assert.equal(tree.regions[0]?.states[0]?.places[0]?.label, "Sandy Pond");
  assert.equal(tree.regions[0]?.locatedCount, 1);
});

test("view=mindmap round-trips in national filter serialization", () => {
  const filters = parseNationalFilters({ view: "mindmap", region: "1" });
  assert.equal(filters.view, "mindmap");
  const query = serializeNationalFilters(filters);
  assert.match(query, /view=mindmap/);
  assert.deepEqual(parseNationalFilters(Object.fromEntries(new URLSearchParams(query))), filters);
  assert.equal(serializeNationalFilters(parseNationalFilters({})).includes("view="), false);
});

test("mind map truncates honestly at the safety limit", async () => {
  const raw = JSON.parse(await readFile(new URL("../../../data/national/projects.json", import.meta.url), "utf8")) as NationalProject[];
  const sample = raw.slice(0, 5);
  const tree = buildMindMapTree(sample, geography, { limit: 2 });
  assert.equal(tree.meta.total, 5);
  assert.equal(tree.meta.included, 2);
  assert.equal(tree.meta.truncated, true);
});
