import assert from "node:assert/strict";
import test from "node:test";
import { calmAt, yearPxAt } from "./timeScale";

test("a year grows by √2 per zoom level, not 2×", () => {
  assert.equal(yearPxAt(3.5, 8, 1e6), 12);
  assert.ok(Math.abs(yearPxAt(5.5, 8, 1e6) / yearPxAt(3.5, 8, 1e6) - 2) < 1e-9);
});

test("the axis never outgrows the room, and a year never vanishes", () => {
  assert.equal(yearPxAt(12, 8, 400), 50);
  assert.equal(yearPxAt(0, 8, 400), 8);
  assert.equal(yearPxAt(12, 100, 400), 8);
});

test("the overview is quiet and a region is fully lit", () => {
  assert.equal(calmAt(1), 0.25);
  assert.equal(calmAt(2.5), 0.25);
  assert.ok(calmAt(3.5) > 0.25 && calmAt(3.5) < 0.4);
  assert.equal(calmAt(4.2), 0.4);
  assert.ok(calmAt(5.35) > 0.4 && calmAt(5.35) < 1);
  assert.equal(calmAt(6.5), 1);
  assert.equal(calmAt(12), 1);
});
