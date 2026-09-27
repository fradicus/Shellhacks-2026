import assert from "node:assert/strict";
import test from "node:test";
import {
  currentProjects, exportHref, parseLegacyResult, projectRecords, resultMatches, serializeLegacyResult, type LegacyResult,
} from "../../../web/lib/legacy/contract.ts";
import type { MatchRow, Project } from "../../../web/lib/types.ts";

// Explicit test-only records; nothing here enters the application.
const project = (id: string, key: string, active: boolean, name = key): Project =>
  ({ _id: id, project_key: key, active, utility: "GPC", name } as unknown as Project);
const match = (id: string, a: string, b: string, view: MatchRow["view"]): MatchRow => ({ _id: id, a, b, view } as unknown as MatchRow);

test("a result round-trips through the URL, and defaults stay out of it", () => {
  const result: LegacyResult = { view: "historical", records: "all_versions", selection: { kind: "project", key: "GPC:1" } };
  const params = serializeLegacyResult(result, "future");
  assert.equal(params.toString(), "view=historical&records=all_versions&project=GPC%3A1");
  assert.deepEqual(parseLegacyResult(params, "future"), result);
  assert.equal(serializeLegacyResult({ view: "future", records: "current", selection: null }, "future").toString(), "");
  assert.deepEqual(parseLegacyResult({ view: "bogus", records: "bogus", pair: "<script>" }, "tentative"),
    { view: "tentative", records: "current", selection: null });
  assert.deepEqual(parseLegacyResult({ pair: "A__B", project: "X" }, "future").selection, { kind: "pair", id: "A__B" });
});

test("the export link carries exactly the result being looked at", () => {
  const result: LegacyResult = { view: "historical", records: "all_versions", selection: { kind: "project", key: "GPC:1" } };
  assert.equal(exportHref("matches", result), "/api/export?type=matches&view=historical&project=GPC%3A1");
  assert.equal(exportHref("projects", result), "/api/export?type=projects&records=all_versions&project=GPC%3A1");
  assert.equal(exportHref("matches", { ...result, selection: { kind: "pair", id: "A__B" } }), "/api/export?type=matches&view=historical&pair=A__B");
  assert.equal(exportHref("projects", { ...result, selection: { kind: "pair", id: "A__B" } }), "/api/export?type=projects&records=all_versions");
});

test("current records: one per key, the active filing's; all versions keeps every filing", () => {
  const rows = [project("b@old", "K1", false), project("a@new", "K1", true), project("c@only", "K2", false), project("d@x", "K3", false),
    project("e@y", "K3", false)];
  const { current, superseded } = currentProjects(rows);
  assert.equal(superseded, 2);
  assert.deepEqual(current.map((p) => p._id).sort(), ["a@new", "c@only", "d@x"]);
  assert.equal(projectRecords(rows, "current").length, 3);
  assert.equal(projectRecords(rows, "all_versions").length, 5);
  assert.deepEqual(rows.map((p) => p._id), ["b@old", "a@new", "c@only", "d@x", "e@y"], "inputs are not reordered");
});

test("the pairs a result covers follow its view and selection", () => {
  const rows = [match("p1", "A", "B", "historical"), match("p2", "A", "C", "future"), match("p3", "C", "D", "historical")];
  assert.deepEqual(resultMatches(rows, { view: "historical", selection: null }).map((m) => m._id), ["p1", "p3"]);
  assert.deepEqual(resultMatches(rows, { view: "historical", selection: { kind: "project", key: "A" } }).map((m) => m._id), ["p1"]);
  assert.deepEqual(resultMatches(rows, { view: "historical", selection: { kind: "pair", id: "p3" } }).map((m) => m._id), ["p3"]);
});
