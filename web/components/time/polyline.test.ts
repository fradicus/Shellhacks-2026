import assert from "node:assert/strict";
import test from "node:test";
import { decodePolyline, roadPath } from "./polyline";

// The published example of the encoded polyline algorithm (precision 5).
const EXAMPLE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@";

test("decodes the reference polyline to [lng, lat]", () => {
  assert.deepEqual(decodePolyline(EXAMPLE), [
    [-120.2, 38.5],
    [-120.95, 40.7],
    [-126.453, 43.252],
  ]);
});

test("a routed path starts and ends at the two stored centers", () => {
  const a = { lat: 38.4, lon: -120.1 };
  const b = { lat: 43.3, lon: -126.5 };
  const path = roadPath(a, b, { polyline: EXAMPLE, start: { lat: 38.5, lon: -120.2 }, end: { lat: 43.26, lon: -126.46 } })!;
  assert.deepEqual(path[0], [a.lon, a.lat]);
  assert.deepEqual(path.at(-1), [b.lon, b.lat]);
  assert.deepEqual(path.slice(1, 4), [[-120.2, 38.5], [-120.95, 40.7], [-126.453, 43.252]]);
  assert.equal(path.length, 6);
});

test("no stored polyline keeps the straight link", () => {
  const a = { lat: 1, lon: 2 };
  assert.equal(roadPath(a, a, null), null);
  assert.equal(roadPath(a, a, { polyline: null }), null);
  assert.equal(roadPath(a, a, { polyline: "" }), null);
});
