import assert from "node:assert/strict";
import test from "node:test";
import { RouteRequestSchema } from "../../../web/lib/operations/contracts.ts";
import { FAILURES, inputFailure, OperationsError, serviceFailure } from "../../../web/lib/operations/errors.ts";
import { POST as postRoute } from "../../../web/app/api/operations/route/route.ts";
import { GET as getConditions } from "../../../web/app/api/operations/conditions/route.ts";
import { GET as getSite } from "../../../web/app/api/operations/site/route.ts";
import { GET as getWater } from "../../../web/app/api/operations/water/route.ts";

// Synthetic requests only; no provider is contacted in these cases.
const truck = { height_m: 4, width_m: 2.5, length_m: 20, gross_weight_kg: 30000, axle_count: 5, trailers: [{ length_m: 15 }], hazmat: [] };
const point = { lat: 47.6, lon: -122.3 };
const post = (body: unknown, headers: Record<string, string> = { "content-type": "application/json" }) =>
  postRoute(new Request("http://gridbridge.test/api/operations/route", { method: "POST", headers, body: typeof body === "string" ? body : JSON.stringify(body) }));

test("each failure class has its own status and a code", () => {
  const statuses = Object.fromEntries(Object.entries(FAILURES).map(([code, { status }]) => [code, status]));
  assert.deepEqual(statuses, { invalid_input: 400, body_too_large: 413, departure_window: 422, not_configured: 503, publication_failure: 503,
    provider_failure: 502, timeout: 504, internal: 500 });
});

test("input errors are the caller's; service errors are classified by cause", () => {
  assert.equal(inputFailure(new SyntaxError("Unexpected token")), "invalid_input");
  assert.equal(inputFailure(new OperationsError("body_too_large")), "body_too_large");
  assert.equal(inputFailure(new Error("Request body deadline exceeded")), "timeout");
  assert.equal(serviceFailure(new OperationsError("departure_window")), "departure_window");
  assert.equal(serviceFailure(new OperationsError("not_configured")), "not_configured");
  assert.equal(serviceFailure(new Error("Provider deadline exceeded")), "timeout");
  assert.equal(serviceFailure(Object.assign(new Error("aborted"), { name: "TimeoutError" })), "timeout");
  assert.equal(serviceFailure(new TypeError("fetch failed")), "provider_failure");
  assert.equal(serviceFailure(RouteRequestSchema.safeParse({}).error), "provider_failure");
  assert.equal(serviceFailure(new Error("something unexpected")), "internal");
});

test("route: malformed input is 400, an oversized body 413, a departure outside the window 422", async () => {
  const bad = await post("{not json");
  assert.equal(bad.status, 400);
  assert.deepEqual(await bad.json(), { error: "Invalid route request", code: "invalid_input" });
  assert.equal((await post({ origin: point }, { "content-type": "text/plain" })).status, 400);
  const big = await post({ pad: "x".repeat(5000) });
  assert.equal(big.status, 413);
  assert.equal((await big.json()).code, "body_too_large");
  const late = await post({ origin: point, destination: point, departure_at: new Date(Date.now() + 30 * 86_400_000).toISOString(), truck });
  assert.equal(late.status, 422);
  assert.deepEqual(await late.json(), { error: "Departure must be now through seven days ahead", code: "departure_window" });
});

test("conditions, site and water: bad queries are 400 with a code and never reach a provider", async () => {
  for (const [handler, url] of [[getConditions, "http://x/api/operations/conditions?lat=abc&lon=1"], [getSite, "http://x/api/operations/site?lat=1"], [getWater, "http://x/api/operations/water?lon=1"]] as const) {
    const res = await handler(new Request(url));
    assert.equal(res.status, 400);
    assert.equal((await res.json()).code, "invalid_input");
  }
});
