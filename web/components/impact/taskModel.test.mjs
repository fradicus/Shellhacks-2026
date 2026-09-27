import assert from "node:assert/strict";
import { test } from "node:test";
import { calculateShare, calculateTask, emptyShare, emptyTask, parseWindows, splitProRata } from "./taskModel.ts";

// SYNTHETIC TEST INPUTS: not quotes or rates for any utility.
const filled = {
  productiveHours: "48", paidHoursPerDay: "10", laborRate: "185", equipRate: "320", siteMultiplier: "1.5",
  siteBasis: "test basis", permitCost: "18500", standbyPerDay: "5050", windows: "6.5, 5.8, 0, 4.9, 7.2, 7.5, 8, 8, 8",
};

test("blank inputs stay unknown and a multiplier without a basis never calculates", () => {
  assert.equal(calculateTask(emptyTask()).result, null);
  assert.equal(calculateTask(emptyTask()).missing, 9);
  const noBasis = calculateTask({ ...filled, siteBasis: " " });
  assert.equal(noBasis.result, null);
  assert.equal(noBasis.missing, 1);
});

test("a restricted window adds paid days; closed days bill standby; totals are exact cents", () => {
  const { result } = calculateTask(filled);
  assert.equal(result.workDays, 8);
  assert.equal(result.deadDays, 1);
  assert.equal(result.paidCrew, 4_040_000);
  assert.equal(result.siteAdjusted, 6_060_000);
  assert.equal(result.siteExtra, 2_020_000);
  assert.equal(result.standby, 505_000);
  assert.equal(result.total, 8_415_000);
  assert.equal(result.windowFactor, 0.6);
  assert.equal(result.idleHours, 32);
});

test("too few listed days reports the unscheduled shortfall instead of a number", () => {
  const out = calculateTask({ ...filled, windows: "6.5, 5.8" });
  assert.equal(out.result, null);
  assert.equal(out.shortfallHours, 35.7);
});

test("explicit zero standby and permit are allowed; multiplier below 1 and bad windows are rejected", () => {
  assert.equal(calculateTask({ ...filled, standbyPerDay: "0", permitCost: "0" }).result.total, 6_060_000);
  assert.ok(calculateTask({ ...filled, siteMultiplier: "0.8" }).errors.siteMultiplier);
  assert.ok(calculateTask({ ...filled, paidHoursPerDay: "25" }).errors.paidHoursPerDay);
  assert.ok(parseWindows("4, 30").error);
  assert.ok(parseWindows("4, -1").error);
  assert.deepEqual(parseWindows("4\n0;2.5").hours, [4, 0, 2.5]);
});

test("pro-rata split always sums to the whole in cents", () => {
  assert.deepEqual(splitProRata(100, [1, 1, 1]), [34, 33, 33]);
  assert.deepEqual(splitProRata(9_000_000, [1.2, 0.8]), [5_400_000, 3_600_000]);
  const parts = splitProRata(1_000_001, [3, 7, 11]);
  assert.equal(parts.reduce((a, b) => a + b, 0), 1_000_001);
});

test("shared item comparison exists only when a build-alone cost is entered, and can be negative", () => {
  assert.equal(calculateShare(emptyShare()).result, null);
  const out = calculateShare({ itemCost: "90000", shareA: "60", shareB: "40", separateA: "50000", separateB: "" }).result;
  assert.equal(out.a, 5_400_000);
  assert.equal(out.b, 3_600_000);
  assert.equal(out.differenceA, -400_000);
  assert.equal(out.differenceB, null);
  assert.ok(calculateShare({ itemCost: "1", shareA: "0", shareB: "0", separateA: "", separateB: "" }).errors.shareB);
});
