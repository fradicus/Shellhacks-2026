import assert from "node:assert/strict";
import test from "node:test";
import {
  applyFilterAction,
  cascadeFilters,
  filterNationalProjects,
  parseNationalFilters,
  serializeNationalFilters,
  validateGeographyFilters,
} from "../../../web/lib/national/filters.ts";
import type { NationalGeography, NationalProject } from "../../../web/lib/national/types.ts";
import { toCsv } from "../../../web/app/api/export/csv.ts";

const geography = {
  schema_version: "national-geography-v1",
  authority: "U.S. Census Bureau",
  provenance: { sources: [], notes: [] },
  counts: {},
  regions: [{ region_code: "1", name: "Northeast", bounds: null }, { region_code: "3", name: "South", bounds: null }],
  divisions: [],
  states: [
    { state_fips: "25", usps: "MA", name: "Massachusetts", scope: "state", selectable_primary: true, census_region_code: "1", census_division_code: "1", bounds: null },
    { state_fips: "13", usps: "GA", name: "Georgia", scope: "state", selectable_primary: true, census_region_code: "3", census_division_code: "5", bounds: null },
    { state_fips: "72", usps: "PR", name: "Puerto Rico", scope: "territory", selectable_primary: false, census_region_code: null, census_division_code: null, bounds: null },
  ],
  counties: [
    { county_geoid: "25001", state_fips: "25", county_fips: "001", name: "Barnstable", full_name: "Barnstable County", state_usps: "MA", state_name: "Massachusetts", scope: "state", selectable_primary: true, bounds: null },
    { county_geoid: "13001", state_fips: "13", county_fips: "001", name: "Appling", full_name: "Appling County", state_usps: "GA", state_name: "Georgia", scope: "state", selectable_primary: true, bounds: null },
  ],
} satisfies NationalGeography;

const project = (overrides: Partial<NationalProject>): NationalProject => ({
  _id: "test-only:one", source_id: "test-only-source", native_id: "T-1", name: "Harbor reinforcement",
  owner: "Test Utility", other_owners: [], planning_region: "TEST", states: ["25"], counties: ["25001"],
  geography_basis: "test fixture", status: "Planned", status_group: "planned",
  in_service: { raw: "2028", value: "2028", precision: "year" }, center: null,
  location_review: "unlocated", evidence: { page: null, sheet: "Test", row: 2, raw: { clearly: "test-only" } },
  ...overrides,
});

test("combined parent and descendant patch survives cascade, while implicit stale children clear", () => {
  const current = parseNationalFilters({ region: "1", state: "25", county: "25001" });
  const combined = cascadeFilters(current, { region: "3", state: "13", county: "13001" });
  assert.equal(combined.region, "3");
  assert.equal(combined.state, "13");
  assert.equal(combined.county, "13001");
  assert.equal(validateGeographyFilters(combined, geography), null);
  assert.equal(cascadeFilters(current, { state: "13" }).county, undefined);
  assert.equal(cascadeFilters(current, { region: "3" }).state, undefined);
});

test("cross-state and cross-region codes fail closed; territory is not put in a Census region", () => {
  assert.equal(validateGeographyFilters(parseNationalFilters({ state: "25", county: "13001" }), geography), "county is not in the selected state");
  assert.equal(validateGeographyFilters(parseNationalFilters({ region: "3", state: "25" }), geography), "state is not in the selected Census region");
  assert.equal(validateGeographyFilters(parseNationalFilters({ state: "72" }), geography), null);
  assert.equal(validateGeographyFilters(parseNationalFilters({ region: "3", state: "72" }), geography), "state is not in the selected Census region");
});

test("partial milestone intervals intersect date filters without inventing exact dates", () => {
  const rows = [
    project({ _id: "test-only:year", in_service: { raw: "2028", value: "2028", precision: "year" } }),
    project({ _id: "test-only:month", in_service: { raw: "March 2028", value: "2028-03", precision: "month" } }),
    project({ _id: "test-only:day", in_service: { raw: "2028-03-20", value: "2028-03-20", precision: "day" } }),
    project({ _id: "test-only:unknown", in_service: { raw: null, value: null, precision: "unknown" } }),
  ];
  const march = parseNationalFilters({ from: "2028-03-15", to: "2028-03-18" });
  assert.deepEqual(filterNationalProjects(rows, march, geography).map((row) => row._id), ["test-only:year", "test-only:month"]);
});

test("unknown geography remains visible until a supported geography filter is applied", () => {
  const unknown = project({ _id: "test-only:unknown-place", states: [], counties: [] });
  assert.deepEqual(filterNationalProjects([unknown], parseNationalFilters({}), geography).map((row) => row._id), [unknown._id]);
  assert.deepEqual(filterNationalProjects([unknown], parseNationalFilters({ state: "25" }), geography), []);
});

test("text is literal, case-insensitive and must match within one field", () => {
  const row = project({ name: "Alpha.* station", description: "separate words" });
  assert.equal(filterNationalProjects([row], parseNationalFilters({ text: ".*" }), geography).length, 1);
  assert.equal(filterNationalProjects([row], parseNationalFilters({ text: "STATION" }), geography).length, 1);
  assert.equal(filterNationalProjects([row], parseNationalFilters({ text: "station Test" }), geography).length, 0);
});

test("URL serialization is stable and reverse dates are rejected", () => {
  const filters = parseNationalFilters({ county: "25001", state: "25", region: "1", text: "harbor", page: "2", limit: "25" });
  const query = serializeNationalFilters(filters);
  assert.equal(query, "region=1&state=25&county=25001&text=harbor&page=2&limit=25");
  assert.deepEqual(parseNationalFilters(Object.fromEntries(new URLSearchParams(query))), filters);
  assert.throws(() => parseNationalFilters({ from: "2029-01-01", to: "2028-12-31" }), /from must not be after to/);
});

test("filter actions stay typed and reset keeps the user's page size", () => {
  const current = parseNationalFilters({ state: "25", limit: "25" });
  assert.equal(applyFilterAction(current, { type: "filters.patch", filters: { text: "harbor" } })?.text, "harbor");
  assert.deepEqual(applyFilterAction(current, { type: "filters.reset" }), { page: 1, limit: 25 });
  assert.equal(applyFilterAction(current, { type: "project.select", projectId: "x" }), null);
});

test("CSV keeps numeric coordinates numeric and neutralizes text formula prefixes", () => {
  const csv = toCsv(["value"], [[-81.2], ["=1+1"], ["\t=1+1"], ["\r=1+1"]]);
  assert.equal(csv, "value\r\n-81.2\r\n'=1+1\r\n'\t=1+1\r\n\"'\r=1+1\"\r\n");
});
