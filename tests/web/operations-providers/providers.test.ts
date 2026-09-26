import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { RouteRequestSchema, parseSiteQuery } from "../../../web/lib/operations/contracts.ts";
import { transport } from "../../../web/lib/operations/transport.ts";
import { weather, soil, roadwork, truckRoute, type Context } from "../../../web/lib/operations/providers.ts";
import { validateSnapshot, aef } from "../../../web/lib/operations/aef.ts";
import { sampleRoute, route } from "../../../web/lib/operations/service.ts";

const now = new Date("2026-09-26T20:00:00Z");
const point = { lat: 47.6062, lon: -122.3321 };
const request = { origin: point, destination: point, departure_at: now.toISOString(), truck: { height_m: 4, width_m: 2.5, length_m: 20, gross_weight_kg: 30000, axle_count: 5, trailers: [{ length_m: 15 }], hazmat: [] } };
const wrap = (value: unknown) => ({ value, hash: "a".repeat(64), retrieved: now.toISOString() });
const ctx = (value: unknown): Context => ({ now, io: async () => wrap(value), userAgent: "GridBridge test" });

test("strict requests reject missing trailer facts, unsupported hazmat, coerced numbers and duplicated queries", () => {
  assert.equal(RouteRequestSchema.safeParse(request).success, true);
  for (const truck of [{ ...request.truck, trailers: undefined }, { ...request.truck, hazmat: ["RADIOACTIVE"] }, { ...request.truck, axle_count: true }, { ...request.truck, trailers: [{ length_m: 25 }] }, { ...request.truck, width_m: .0001 }]) assert.equal(RouteRequestSchema.safeParse({ ...request, truck }).success, false);
  for (const query of ["lat=1&lon=2&year=2025&year=2025", "lat=NaN&lon=2&year=2025", "lat=1&lon=2&year=2025&url=x", "lat=&lon=2&year=2025"]) assert.throws(() => parseSiteQuery(new URLSearchParams(query)));
});

test("transport blocks arbitrary hosts, redirects, oversized bodies and stalled stream deadlines", async () => {
  let calls = 0;
  const io = transport(async () => { calls++; return new Response("{}", { status: 302 }); }, 30);
  await assert.rejects(io("https://example.com")); assert.equal(calls, 0);
  await assert.rejects(io("https://api.weather.gov/points/1,2"));
  const big = transport(async () => new Response("123456"), 50);
  await assert.rejects(big("https://api.weather.gov", {}, 5), /budget/);
  let cancelled = false;
  const stalled = transport(async () => new Response(new ReadableStream({ cancel() { cancelled = true; } })), 20);
  await assert.rejects(stalled("https://api.weather.gov"), /deadline/); assert.equal(cancelled, true);
});

const forecast = { properties: { generatedAt: now.toISOString(), updateTime: now.toISOString(), validTimes: "2026-09-26T20:00:00Z/PT7D", periods: [{ startTime: now.toISOString(), endTime: "2026-09-26T21:00:00Z", temperature: null, temperatureUnit: null, windSpeed: "5 mph", windDirection: "N", probabilityOfPrecipitation: { value: null }, shortForecast: "Cloudy" }] } };
const alerts = { type: "FeatureCollection", features: [{ id: "alert1", geometry: null, properties: { event: "Flood Watch", severity: "Unknown", certainty: "Possible", urgency: "Future", sent: now.toISOString(), onset: null, expires: "2026-09-27T00:00:00Z", description: "Test only", affectedZones: ["https://api.weather.gov/zones/forecast/WAZ558"] } }] };
function weatherContext(f = forecast, a: unknown = alerts): Context {
  return { now, userAgent: "GridBridge test", io: async (url) => wrap(url.includes("/points/") ? { properties: { forecastHourly: "https://api.weather.gov/gridpoints/SEW/1,2/forecast/hourly", gridId: "SEW", gridX: 1, gridY: 2 } } : url.includes("/alerts/") ? a : f) };
}
test("weather preserves null polygon warnings and unknown numbers; stale/future/malformed responses fail visibly", async () => {
  const good = await weather(point, weatherContext());
  assert.equal(good.status, "available"); assert.equal(good.data?.samples[0].alerts.length, 1); assert.equal(good.data?.samples[0].forecast[0].temperature, null);
  const stale = structuredClone(forecast); stale.properties.updateTime = "2026-09-25T00:00:00Z";
  assert.equal((await weather(point, weatherContext(stale))).status, "stale");
  const future = structuredClone(forecast); future.properties.updateTime = "2027-01-01T00:00:00Z";
  assert.equal((await weather(point, weatherContext(future))).status, "unavailable");
  assert.equal((await weather(point, weatherContext(forecast, {}))).status, "unavailable");
  assert.equal((await weather(point, { ...ctx({}), userAgent: undefined })).status, "not_configured");
});
test("soil validates fixed schema and preserves missing component facts", async () => {
  const data = { Table: [["mukey", "muname", "areasymbol", "saverest", "cokey", "compname", "comppct_r", "drainagecl", "hydgrp"], Array(9).fill("metadata"), ["1", "Unit", "WA001", "2025-01-01", "2", "Component", null, null, null]] };
  const result = await soil(point, ctx(data)); assert.equal(result.status, "available"); assert.equal(result.data?.map_units[0].components[0].percent, null);
  assert.equal((await soil(point, ctx({ Table: [] }))).status, "unavailable");
  assert.equal((await soil({ lat: NaN, lon: 0 }, ctx(data))).status, "unavailable");
});
test("unknown road jurisdiction does not call provider or claim zero events", async () => {
  const result = await roadwork({ lat: 32, lon: -80 }, { now, io: async () => { throw new Error("Should not call"); } });
  assert.equal(result.status, "out_of_coverage"); assert.equal(result.data, null);
});
test("Google adapter requires provisioning, sends trailer facts, exposes only summary and flags best effort", async () => {
  assert.equal((await truckRoute(request, ctx({}))).result.status, "not_configured");
  let body: Record<string, unknown> | undefined;
  const result = await truckRoute(request, { now, lvrEnabled: true, googleKey: "synthetic-test-only", io: async (_url, init) => { body = JSON.parse(String(init?.body)); return wrap({ routes: [{ distanceMeters: 1000, duration: "60s", polyline: { encodedPolyline: "??AA" }, travelAdvisory: { routeRestrictionsPartiallyIgnored: true }, warnings: ["Restriction"] }] }); } });
  assert.equal(body?.travelMode, "TRUCK"); assert.match(JSON.stringify(body), /trailerInfo/); assert.equal(result.result.status, "partial");
  assert.equal(result.result.data?.restrictions_partially_ignored, true); assert.equal(result.result.data?.eta, "2026-09-26T20:01:00.000Z");
  assert.doesNotMatch(JSON.stringify(result.result), /encodedPolyline|routeToken|synthetic-test-only/);
});
test("route sampling exposes large gaps; absent truck route leaves assessment incomplete", async () => {
  const sampling = sampleRoute([{ lat: 30, lon: -120 }, { lat: 48, lon: -70 }]); assert.equal(sampling.points.length, 5); assert.equal(sampling.limited, true);
  const result = await route(request, ctx({}), null); assert.equal(result.status, "incomplete"); assert.equal(result.weather.data, null);
  await assert.rejects(route({ ...request, departure_at: "2027-01-01T00:00:00Z" }, ctx({})), /Departure/);
});
test("real AEF artifact binds exact point/year and rejects numeric/hash tampering", async () => {
  const data = JSON.parse(await readFile(new URL("../../../data/environment/aef-samples.json", import.meta.url), "utf8"));
  const snapshot = validateSnapshot(data);
  assert.equal(aef(point, 2025, snapshot, now).status, "available"); assert.equal(aef(point, 2024, snapshot, now).data, null); assert.equal(aef({ ...point, lat: 47 }, 2025, snapshot, now).data, null);
  const changed = structuredClone(data); changed.records[0].embedding[0] += .01; assert.throws(() => validateSnapshot(changed));
  const raw = structuredClone(data); raw.records[0].raw[0] = -128; assert.throws(() => validateSnapshot(raw));
});
