import assert from "node:assert/strict";
import test from "node:test";
import { interval, intersects, legacyHistory, nationalHistory } from "../../../web/lib/history/events.ts";
import type { NationalProject } from "../../../web/lib/national/types.ts";
import type { Project, VersionChange } from "../../../web/lib/types.ts";

// Explicit test-only records; nothing here enters the application.
const ev = (field: string, date: string | null, type = "planned_milestone") => ({
  id: `test:pjm:X1:${field}`, type, date, precision: date ? "day" : "unknown", native_project_link: "X1",
  description: `PJM ${field}: ${date}.`, evidence: [{ publisher: "Test", url: "https://example.test/x", artifact_sha256: "0",
    locator: "/row[1]", source_date: null, retrieved_at: "2026-09-27T00:00:00Z", access_review: "", facts: "" }],
});
const national = (events: unknown[], extra: Partial<NationalProject> = {}) => ({
  _id: "test:1", native_id: "X1", source_id: "test-src", name: "Test upgrade", owner: "T", other_owners: [],
  planning_region: "PJM", states: [], counties: [], geography_basis: null, status: "IS", status_group: "in_service",
  in_service: { value: "2010-06-15", raw: "6/15/2010", precision: "day" }, center: { lat: 40, lon: -75, basis: "source_point", evidence: "" },
  location_review: "confirmed", evidence: { page: null, sheet: "S", row: 4, raw: {} }, project_events: events, ...extra,
}) as unknown as NationalProject;

test("intervals keep their own precision and never pick a day", () => {
  assert.deepEqual(interval("2011-04", "month")!.map((d) => new Date(d * 864e5).toISOString().slice(0, 10)), ["2011-04-01", "2011-05-01"]);
  assert.deepEqual(interval("2012", "year")!.map((d) => new Date(d * 864e5).toISOString().slice(0, 10)), ["2012-01-01", "2013-01-01"]);
  assert.equal(interval("2011-02-30", "day"), null);
  assert.equal(interval(null, "day"), null);
  assert.equal(interval("2011", "unknown"), null);
});

test("range intersection: exact inside, spans overlapping, unknown never", () => {
  const [lo, hi] = interval("2011", "year")!;
  assert.ok(intersects({ from: interval("2011-12-31", "day")![0], to: interval("2011-12-31", "day")![1] }, lo, hi));
  assert.ok(!intersects({ from: interval("2012-01-01", "day")![0], to: interval("2012-01-01", "day")![1] }, lo, hi));
  const month = interval("2010-12", "month")!;
  assert.ok(!intersects({ from: month[0], to: month[1] }, lo, hi));
  assert.ok(intersects({ from: month[0], to: month[1] }, lo - 1, hi));
  assert.ok(!intersects({ from: null, to: null }, lo, hi));
});

test("PJM fields keep planned and actual meanings; the bracket prefers RequiredDate and needs exact dates", () => {
  const h = nationalHistory(national([ev("ProjectedInServiceDate", "2010-06-01"), ev("RequiredDate", "2010-01-01"),
    ev("ActualInServiceDate", "2010-06-15", "in_service"), ev("RevisedInServiceDate", null)]), undefined);
  assert.deepEqual(h.events.map((e) => [e.field, e.meaning]), [
    ["RequiredDate", "plan"], ["ProjectedInServiceDate", "plan"], ["ActualInServiceDate", "actual"], ["RevisedInServiceDate", "plan"],
  ]);
  assert.equal(h.thread?.days, 165);
  assert.equal(h.thread?.text, "In service 165 days after the required date");
  assert.equal(nationalHistory(national([ev("RequiredDate", "2010-01-01")]), undefined).thread, null);
});

test("an ISO-NE projected month is a plan span, and the register status is not an actual date", () => {
  const h = nationalHistory(national([], { planning_region: "iso-ne", status: "In-service",
    in_service: { value: "2011-04", raw: "2011-04-01T00:00:00", precision: "month" } }), undefined);
  assert.equal(h.events.length, 1);
  assert.equal(h.events[0].meaning, "plan");
  assert.equal(h.events[0].to! - h.events[0].from!, 30);
  assert.equal(h.thread, null);
  assert.equal(h.status, "In-service");
});

test("legacy revisions draw old → new filed dates; one project stays one project", () => {
  const p = { _id: "DESC:1@desc-2025", project_key: "DESC:1", utility: "DESC", owner_code: null, native_id: "1", name: "L",
    source: { source_id: "desc-2025", page: 2 }, in_service: { raw: "5/31/2026", date: "2026-05-31", precision: "day" }, active: true,
    center: { lat: 33, lon: -80 } } as Project;
  const changes: VersionChange[] = [
    { _id: "DESC:1|in_service.date|desc-2024>desc-2025", project_key: "DESC:1", field: "in_service.date", old: "2024-12-31",
      new: "2026-05-31", from_source: "desc-2024", to_source: "desc-2025", from_page: 3, to_page: 2 },
    { _id: "DESC:1|cost_usd|desc-2024>desc-2025", project_key: "DESC:1", field: "cost_usd", old: 1, new: 2,
      from_source: "desc-2024", to_source: "desc-2025" },
  ];
  const h = legacyHistory(p, changes, new Map());
  assert.equal(h.events.length, 2);
  assert.equal(h.events[0].superseded, "desc-2025");
  assert.equal(h.thread?.days, 516);
  assert.match(h.thread!.text, /^Moved 516 days later between desc-2024 and desc-2025$/);
});
