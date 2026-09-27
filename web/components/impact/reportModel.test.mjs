import assert from "node:assert/strict";
import { test } from "node:test";
import { DEFAULT_DELAY } from "./delayModel.ts";
import { lastYear } from "./reportModel.ts";

const history = { start: "2016-01-01", prcp_in: Array(3653).fill(0), tmax_f: Array(3653).fill(70), wsf2_mph: Array(3653).fill(5), tmin_f: Array(3653).fill(50), snow_in: Array(3653).fill(0) };
const recent = (start, days, rainAt = {}) => ({ start, end: new Date(Date.parse(`${start}T00:00:00Z`) + (days - 1) * 86400000).toISOString().slice(0, 10), source_url: "https://www.ncei.noaa.gov/x",
  prcp_in: Array.from({ length: days }, (_, i) => rainAt[i] ?? 0), tmax_f: Array(days).fill(70), tmin_f: Array(days).fill(50), snow_in: Array(days).fill(0), wsf2_mph: null });

test("this time last year prefers recent NOAA observations and reports the real delay", () => {
  const r = recent("2025-08-20", 400, { 42: 1.2 }); // 2025-10-01, a Wednesday
  const ly = lastYear(history, r, "2026-10-01", { ...DEFAULT_DELAY, workdays: "5" }, 14);
  assert.equal(ly.from, "recent"); assert.equal(ly.year, 2025); assert.equal(ly.start, "2025-10-01");
  assert.deepEqual(ly.days[0].reasons, ["rain"]);
  assert.equal(ly.run.stops.rain, 1); assert.ok(ly.run.extraDays >= 1);
  assert.equal(ly.days.length, 14);
});

test("falls back to the 10-year record, and returns null when neither covers last year", () => {
  const ly = lastYear(history, null, "2024-03-10", DEFAULT_DELAY, 10);
  assert.equal(ly.from, "record"); assert.equal(ly.start, "2023-03-10");
  assert.equal(lastYear(history, null, "2030-03-10", DEFAULT_DELAY, 10), null);
  assert.equal(lastYear(history, null, "2025-03-01", DEFAULT_DELAY, 3).start, "2024-03-01");
});
