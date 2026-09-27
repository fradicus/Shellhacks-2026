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

test("day details summarize one calendar day across recorded years and prefer recent data for last year", async () => {
  const { dayDetails } = await import("./reportModel.ts");
  const h = { ...history, prcp_in: [...history.prcp_in], tmax_f: [...history.tmax_f], tmin_f: [...history.tmin_f] };
  h.prcp_in[9] = 1.1; h.tmax_f[9] = 60; // 2016-01-10
  const d = dayDetails(h, recent("2025-01-01", 30, { 9: 0.6 }), "2026-01-10", DEFAULT_DELAY);
  assert.equal(d.years.length, 10); assert.equal(d.recorded, 10);
  assert.equal(d.stopShare, 0.1); assert.equal(d.wetYears, 1); assert.equal(d.maxRain, 1.1);
  assert.equal(d.avgHigh, 69); assert.equal(d.avgLow, 50);
  assert.deepEqual([d.lastYear.date, d.lastYear.from, d.lastYear.reasons], ["2025-01-10", "recent", ["rain"]]);
  const leap = dayDetails(h, null, "2028-02-29", DEFAULT_DELAY);
  assert.deepEqual(leap.years.map((y) => y.year), [2016, 2020, 2024]);
  assert.equal(leap.lastYear, null); // 2027-02-29 does not exist
});
