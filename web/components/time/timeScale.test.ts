import assert from "node:assert/strict";
import test from "node:test";
import { yearPxAt } from "./timeScale";

test("a year grows by √2 per zoom level, not 2×", () => {
  assert.equal(yearPxAt(3.5, 8, 1e6), 20);
  assert.ok(Math.abs(yearPxAt(5.5, 8, 1e6) / yearPxAt(3.5, 8, 1e6) - 2) < 1e-9);
});

test("the axis never outgrows the room, and a year never vanishes", () => {
  assert.equal(yearPxAt(12, 8, 400), 50);
  assert.equal(yearPxAt(0, 8, 400), 8);
  assert.equal(yearPxAt(12, 100, 400), 8);
});
