import assert from "node:assert/strict";
import test from "node:test";
import { nationalTimeProjects } from "./nationalProjects";
import { epochYear, span } from "./timeScale";
import type { NationalProject, NationalSource } from "../../lib/national/types";

// Explicit test-only records; no synthetic data enters the application.
const project: NationalProject = {
  _id: "test-national:1", native_id: "1", source_id: "test-source", name: "Test project",
  owner: "Test owner", other_owners: [], planning_region: null, states: [], counties: [],
  geography_basis: null, status: "Planned", status_group: "planned",
  in_service: { value: "2028-04", raw: "April 2028", precision: "month" },
  center: { lat: 42, lon: -72, basis: "one", evidence: "Test-only endpoint" },
  location_review: "confirmed", evidence: { page: 2, sheet: null, row: 3, raw: {} },
};

test("national projection excludes legacy duplicates and unapproved or invalid points, preserving facts", () => {
  const source = { _id: "test-source", publisher: "Test publisher" } as NationalSource;
  const rows = [project, { ...project, _id: "legacy:1" },
    { ...project, _id: "test-national:2", location_review: "unreviewed" as const },
    { ...project, _id: "test-national:3", location_review: "rejected" as const },
    { ...project, _id: "test-national:4", center: null },
    { ...project, _id: "test-national:5", center: { ...project.center!, lat: NaN } }];
  const result = nationalTimeProjects(rows, [source]);
  assert.equal(result.length, 1);
  assert.equal(result[0].key, project._id);
  assert.deepEqual(result[0].in_service, { date: "2028-04", raw: "April 2028", precision: "month" });
  assert.equal(result[0].national?.project, project);
  assert.equal(result[0].national?.source, source);
  assert.equal(result[0].center?.lat, 42);
  assert.equal(result[0].national?.project.owner, "Test owner");
  assert.equal(result[0].national?.project.center?.basis, "one");
});

test("partial milestones remain intervals and legacy exact dates stay exact", () => {
  const month = { date: "2028-04", raw: "April 2028", precision: "month" as const };
  const year = { date: "2027", raw: "2027", precision: "year" as const };
  const unknown = { date: "1900-01-01", raw: "Unknown", precision: "unknown" as const };
  assert.equal(epochYear([month, year, unknown]), 2027);
  assert.deepEqual(span(month, 2028), { kind: "range", from: 91, to: 121, precision: "month", label: "2028-04" });
  assert.deepEqual(span(year, 2027), { kind: "range", from: 0, to: 365, precision: "year", label: "2027" });
  assert.deepEqual(span({ ...month, date: "2028-04-01" }, 2028), span(month, 2028));
  assert.deepEqual(span({ date: "2028-04-02", precision: "day", raw: "4/2/2028" }, 2028),
    { kind: "exact", day: 92, iso: "2028-04-02" });
  assert.deepEqual(span(unknown, 2028), { kind: "unknown" });
  assert.deepEqual(span({ ...month, date: null }, 2028), { kind: "unknown" });
});
