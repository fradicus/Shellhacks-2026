import assert from "node:assert/strict";
import test from "node:test";
import { SLIP_SPAN, slipBins } from "../../../web/lib/history/slip.ts";

test("early gaps fill the left half, late the right, and extremes clamp to the end bins", () => {
  const { counts, early, late, median } = slipBins([-1, -200, 0, 30, 5000, -9000]);
  assert.equal(counts.length, SLIP_SPAN * 2);
  assert.equal(counts[SLIP_SPAN - 1], 1); // -1 day
  assert.equal(counts[SLIP_SPAN - 2], 1); // -200 days
  assert.equal(counts[SLIP_SPAN], 2); // 0 and +30 days
  assert.equal(counts[0], 1); // -9000 clamps left
  assert.equal(counts.at(-1), 1); // +5000 clamps right
  assert.equal(counts.reduce((a, b) => a + b), 6);
  assert.deepEqual([early, late], [3, 2]); // 0 is neither
  assert.equal(median, (-1 + 0) / 2);
});

test("no rows, no median", () => {
  assert.equal(slipBins([]).median, null);
  assert.deepEqual(slipBins([]).counts, Array(SLIP_SPAN * 2).fill(0));
});
