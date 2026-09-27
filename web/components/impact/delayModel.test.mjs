import assert from "node:assert/strict";
import { test } from "node:test";
import { byStartMonth, DEFAULT_DELAY, replay, validate } from "./delayModel.ts";

// 2016-01-01 was a Friday. Synthetic series only; the committed NOAA records are exercised through the API in the browser check.
const series = (days, fill = {}) => ({
  start: "2016-01-01",
  prcp_in: Array.from({ length: days }, (_, i) => fill.rain?.[i] ?? 0),
  tmax_f: Array.from({ length: days }, (_, i) => fill.heat?.[i] ?? 70),
  wsf2_mph: Array.from({ length: days }, (_, i) => fill.wind?.[i] ?? 5),
});
const rules = { rain: 0.5, wind: 28, heat: null };

test("no weather stops means no extra days; weekends only move the baseline", () => {
  const run = replay(series(30), 0, 5, rules, true, 2016);
  // Fri 1, Mon 4 .. Thu 7 → 5 workdays in 7 calendar days
  assert.deepEqual(run, { year: 2016, calendarDays: 7, baselineDays: 7, extraDays: 0, stops: { rain: 0, wind: 0, heat: 0 }, missing: 0 });
  assert.equal(replay(series(30), 0, 5, rules, false, 2016).calendarDays, 5);
});

test("each rain or wind stop on a workday pushes finish later; weekend weather costs nothing", () => {
  const rain = []; rain[0] = 1.2; rain[2] = 3; // Friday lost; Sunday storm ignored on a weekday-only schedule
  const wind = []; wind[3] = 30; // Monday lost to wind
  const run = replay(series(30, { rain, wind }), 0, 5, rules, true, 2016);
  assert.equal(run.baselineDays, 7);
  assert.equal(run.calendarDays, 11); // Tue 5 .. Fri 8, Mon 11
  assert.equal(run.extraDays, 4);
  assert.deepEqual(run.stops, { rain: 1, wind: 1, heat: 0 });
});

test("missing readings never stop work, are counted, and a rule left blank is off", () => {
  const s = series(30); s.prcp_in[0] = null; s.tmax_f[0] = 101;
  const run = replay(s, 0, 1, rules, false, 2016);
  assert.equal(run.calendarDays, 1); assert.equal(run.missing, 1);
  assert.equal(replay(s, 0, 1, { ...rules, heat: 100 }, false, 2016).calendarDays, 2);
});

test("a task that would run past the record is excluded, not truncated", () => {
  assert.equal(replay(series(10), 0, 20, rules, false, 2016), null);
  const months = byStartMonth(series(366), { ...DEFAULT_DELAY, workdays: "25" }).months;
  assert.equal(months[0].runs.length, 1);
  assert.deepEqual(months[11].excluded, [2016]); // December 2016 has only 22 weekdays, so 25 runs past the record
});

test("monthly summaries use the median, min and max across replayed years", () => {
  // Two years; every January 4th (a workday in both years) is stormy only in 2017.
  const s = series(731); s.prcp_in[366 + 3] = 2; // 2017-01-04
  const jan = byStartMonth(s, { ...DEFAULT_DELAY, workdays: "3" }).months[0];
  assert.deepEqual(jan.runs.map((r) => r.extraDays), [0, 1]);
  assert.equal(jan.medianExtra, 0.5); assert.equal(jan.minExtra, 0); assert.equal(jan.maxExtra, 1); assert.equal(jan.worstYear, 2017);
});

test("inputs are validated, blank rules are allowed and wind is ignored without a wind record", () => {
  assert.ok(validate({ ...DEFAULT_DELAY, workdays: "0" }).errors.workdays);
  assert.ok(validate({ ...DEFAULT_DELAY, rainIn: "-1" }).errors.rainIn);
  assert.equal(validate({ ...DEFAULT_DELAY, rainIn: "", windMph: "" }).rain, null);
  assert.equal(byStartMonth(series(60), { ...DEFAULT_DELAY, rainIn: "", windMph: "" }).rulesOff, true);
  const noWind = { ...series(60, { wind: Array(60).fill(90) }), wsf2_mph: null };
  assert.equal(byStartMonth(noWind, { ...DEFAULT_DELAY, workdays: "5" }).months[0].runs[0].extraDays, 0);
});
