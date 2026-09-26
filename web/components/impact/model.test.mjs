import assert from "node:assert/strict";
import { test } from "node:test";
import { calculate, emptyInputs, milestoneGap } from "./model.ts";

test("blank and malformed assumptions stay unknown; explicit zero and negative results survive", () => {
  assert.equal(calculate(emptyInputs(), false).result, null);
  const input = { ...emptyInputs(), mobilizations: "2", unitCost: "1000.10", coordinationCost: "500.20" };
  assert.equal(calculate(input, false).result.net, 150000);
  assert.equal(calculate({ ...input, coordinationCost: "2500.20" }, false).result.net, -50000);
  assert.equal(calculate({ ...input, mobilizations: "0", unitCost: "0", coordinationCost: "0" }, false).result.net, 0);
  for (const value of ["-1", "NaN", "Infinity", "1e3", "1,000", "1.234", "1000000001"]) {
    assert.equal(calculate({ ...input, unitCost: value }, false).result, null, value);
  }
  assert.equal(calculate({ ...input, mobilizations: "1.5" }, false).result, null);
  assert.equal(calculate({ ...input, mobilizations: "1000000", unitCost: "1000000000" }, false).overflow, true);
});

test("holding cost is opt-in, requires explicit inputs and uses package-wide daily rate", () => {
  const input = { mobilizations: "2", unitCost: "1000", coordinationCost: "500", idleDays: "4", dailyRate: "200" };
  assert.equal(calculate(input, false).result.net, 150000);
  assert.equal(calculate(input, true).result.net, 70000);
  assert.equal(calculate(input, true).result.maxIdleDays, 7);
  assert.equal(calculate({ ...input, idleDays: "8" }, true).result.net, -10000);
  assert.equal(calculate({ ...input, dailyRate: "" }, true).result, null);
  assert.equal(calculate({ ...input, dailyRate: "0" }, true).result.maxIdleDays, null);
});

test("hypothetical milestone gap rejects invalid dates and handles leap days and DST", () => {
  assert.equal(milestoneGap("", "2026-01-01"), null);
  assert.equal(milestoneGap("2026-02-30", "2026-03-01"), null);
  assert.equal(milestoneGap("2026-02", "2026-03-01"), null);
  assert.equal(milestoneGap("2024-02-28", "2024-03-01"), 2);
  assert.equal(milestoneGap("2026-03-09", "2026-03-07"), 2);
  assert.equal(milestoneGap("2026-01-01", "2026-01-01"), 0);
});
