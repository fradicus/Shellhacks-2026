import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { RouteRequestSchema, parseSiteQuery, parseConditionsQuery, millimeters } from "../../../web/lib/operations/contracts.ts";
import { GET as getConditions } from "../../../web/app/api/operations/conditions/route.ts";
import { washingtonContains } from "../../../web/lib/operations/jurisdiction.ts";
import { transport } from "../../../web/lib/operations/transport.ts";
import { weather, soil, roadwork, truckRoute, context, DEFAULT_NWS_USER_AGENT, type Context } from "../../../web/lib/operations/providers.ts";
import { validateSnapshot, aef } from "../../../web/lib/operations/aef.ts";
import { sampleRoute, route, conditions, reference } from "../../../web/lib/operations/service.ts";

const now = new Date("2026-09-26T20:00:00Z");
const point = { lat: 47.6062, lon: -122.3321 };
const request = { origin: point, destination: point, departure_at: now.toISOString(), truck: { height_m: 4, width_m: 2.5, length_m: 20, gross_weight_kg: 30000, axle_count: 5, trailers: [{ length_m: 15 }], hazmat: [] } };
const wrap = (value: unknown) => ({ value, hash: "a".repeat(64), retrieved: now.toISOString() });
const ctx = (value: unknown): Context => ({ now, io: async () => wrap(value), userAgent: "GridBridge test" });

test("NWS has a public identifying contact by default and respects an explicit override", async () => {
  const prior = process.env.NWS_USER_AGENT;
  try {
    delete process.env.NWS_USER_AGENT;
    assert.equal(context().userAgent, DEFAULT_NWS_USER_AGENT);
    assert.equal((await reference(context())).providers.find((p) => p.id === "weather")?.ready, true);
    process.env.NWS_USER_AGENT = "GridBridge deployment (https://example.org/contact)";
    assert.equal(context().userAgent, process.env.NWS_USER_AGENT);
    process.env.NWS_USER_AGENT = "  "; assert.equal(context().userAgent, DEFAULT_NWS_USER_AGENT);
  } finally { if (prior === undefined) delete process.env.NWS_USER_AGENT; else process.env.NWS_USER_AGENT = prior; }
});

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

test("conditions refresh calls only weather and roadwork, validates strict points and rejects query drift", async () => {
  const calls: string[] = [];
  const weatherCtx = weatherContext();
  const result = await conditions(point, { ...weatherCtx, googleKey: "synthetic-test-only", lvrEnabled: true, io: async (url, ...rest) => {
    calls.push(url);
    if (new URL(url).hostname === "wzdx.wsdot.wa.gov") return wrap({ type: "FeatureCollection", feed_info: { publisher: "WSDOT", version: "4.2", update_date: now.toISOString() }, features: [] });
    assert.equal(new URL(url).hostname, "api.weather.gov");
    return weatherCtx.io(url, ...rest);
  } });
  assert.deepEqual(Object.keys(result).sort(), ["request", "roadwork", "weather"]);
  assert.equal(result.weather.status, "available"); assert.equal(result.roadwork.status, "available");
  assert.equal(calls.length, 4); assert.equal(calls.filter((url) => new URL(url).hostname === "wzdx.wsdot.wa.gov").length, 1);
  assert.deepEqual(parseConditionsQuery(new URLSearchParams("lat=47.6062&lon=-122.3321")), point);
  await assert.rejects(conditions({ lat: 91, lon: 0 }, weatherCtx));
  for (const query of ["lat=1&lon=2&year=2025", "lat=1&lon=2&lat=1", "lat=91&lon=2", "lat=1&lon=181", "lat=NaN&lon=2", "lat=1e2&lon=2", "lat=&lon=2", "lat=1", "lat=1&lon=2&url=x"]) {
    assert.throws(() => parseConditionsQuery(new URLSearchParams(query)));
    const response = await getConditions(new Request(`https://gridbridge.test/api/operations/conditions?${query}`));
    assert.equal(response.status, 400); assert.equal(response.headers.get("cache-control"), "no-store");
  }
});
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
  const evidence = JSON.parse(await readFile(new URL("../../../data/environment/aef-samples.evidence.json", import.meta.url), "utf8"));
  const snapshot = validateSnapshot(data, evidence);
  assert.equal(aef(point, 2025, snapshot, now).status, "available"); assert.equal(aef(point, 2024, snapshot, now).data, null); assert.equal(aef({ ...point, lat: 47 }, 2025, snapshot, now).data, null);
  assert.equal(aef(point, 2025, snapshot, now).retrieved_at, new Date(evidence.records[0].retrieved_at).toISOString());
  const changed = structuredClone(data); changed.records[0].embedding[0] += .01; assert.throws(() => validateSnapshot(changed, evidence));
  const raw = structuredClone(data); raw.records[0].raw[0] = -128; assert.throws(() => validateSnapshot(raw, evidence));
  for (const field of ["object_etag", "index_sha256", "sample_sha256"]) { const bad = structuredClone(evidence); bad.records[0][field] = "f".repeat(64); assert.throws(() => validateSnapshot(data, bad)); }
  const noRanges = structuredClone(evidence); noRanges.records[0].ranges = []; assert.throws(() => validateSnapshot(data, noRanges));
});

test("vehicle conversion requires exact mm/kg and preserves 1.001m without floating floor loss", () => {
  assert.equal(millimeters(1.001), 1001);
  for (const truck of [{ ...request.truck, height_m: 4.0001 }, { ...request.truck, gross_weight_kg: 30000.99 }, { ...request.truck, trailers: [{ length_m: 15.0001 }] }]) assert.equal(RouteRequestSchema.safeParse({ ...request, truck }).success, false);
});
test("soil distinguishes exactly1000rows from1001sentinel and preserves1000rows", async () => {
  const header = ["mukey", "muname", "areasymbol", "saverest", "cokey", "compname", "comppct_r", "drainagecl", "hydgrp"];
  const rows = Array.from({ length: 1001 }, (_, i) => [String(i), "Unit", "WA001", "2025-01-01", String(i), "Component", null, null, null]);
  const exact = await soil(point, ctx({ Table: [header, header, ...rows.slice(0, 1000)] }));
  assert.equal(exact.status, "available"); assert.equal(exact.coverage.truncated, false);
  const more = await soil(point, ctx({ Table: [header, header, ...rows] }));
  assert.equal(more.status, "partial"); assert.equal(more.data?.map_units.length, 1000); assert.equal(more.coverage.truncated, true);
});
test("Census Washington polygon rejects Portland and Idaho within old rectangular prefilter", async () => {
  assert.equal(await washingtonContains(point), true);
  for (const p of [{ lat: 45.52, lon: -122.67 }, { lat: 47.65, lon: -116.9 }]) {
    assert.equal(await washingtonContains(p), false);
    const result = await roadwork(p, { now, io: async () => { throw new Error("must not request"); } }); assert.equal(result.status, "out_of_coverage");
  }
});
test("route transport identity changes aggregate environmental binding and warnings remain partial", async () => {
  function encodedNumber(n: number) { let v = n < 0 ? -n * 2 - 1 : n * 2; let s = ""; while (v >= 32) { s += String.fromCharCode((v % 32) + 95); v = Math.floor(v / 32); } return s + String.fromCharCode(v + 63); }
  const encoded = encodedNumber(Math.round(point.lat * 1e5)) + encodedNumber(Math.round(point.lon * 1e5)) + "??";
  const make = (hash: string): Context => ({ ...weatherContext(), googleKey: "synthetic", lvrEnabled: true, io: async (url, init, max) => url.includes("routes.googleapis.com") ? { ...wrap({ routes: [{ distanceMeters: 0, duration: "1s", polyline: { encodedPolyline: encoded }, warnings: ["Check restrictions"] }] }), hash, retrieved: "2026-09-26T20:00:05Z" } : weatherContext().io(url, init, max) });
  const first = await route(request, make("1".repeat(64)), null); const second = await route(request, make("2".repeat(64)), null);
  assert.equal(first.route.status, "partial"); assert.equal(first.route.retrieved_at, "2026-09-26T20:00:05Z");
  assert.equal(first.route.evidence_hash, "1".repeat(64)); assert.notEqual(first.weather.evidence_hash, second.weather.evidence_hash);
  assert.match(first.limitations.join(" "), /not resolved to per-point arrival/);
});

test("partial AEF aggregate retrieval comes from actual data, not current unavailable samples", async () => {
  const data = JSON.parse(await readFile(new URL("../../../data/environment/aef-samples.json", import.meta.url), "utf8"));
  const evidence = JSON.parse(await readFile(new URL("../../../data/environment/aef-samples.evidence.json", import.meta.url), "utf8"));
  const snapshot = validateSnapshot(data, evidence);
  function encode(n: number) { let v = n < 0 ? -n * 2 - 1 : n * 2; let s = ""; while (v >= 32) { s += String.fromCharCode((v % 32) + 95); v = Math.floor(v / 32); } return s + String.fromCharCode(v + 63); }
  const encoded = encode(Math.round(point.lat * 1e5)) + encode(Math.round(point.lon * 1e5)) + encode(10) + "?";
  const later = new Date(Date.parse(evidence.records[0].retrieved_at) + 3600000);
  const result = await route({ ...request, departure_at: later.toISOString(), destination: { lat: point.lat + .0001, lon: point.lon } }, { now: later, googleKey: "synthetic", lvrEnabled: true, io: async (url) => url.includes("routes.googleapis.com") ? wrap({ routes: [{ distanceMeters: 12, duration: "1s", polyline: { encodedPolyline: encoded } }] }) : wrap({}) }, snapshot);
  assert.equal(result.aef.data?.samples.length, 1); assert.equal(result.aef.coverage.failed, 1);
  assert.equal(result.aef.retrieved_at, new Date(evidence.records[0].retrieved_at).toISOString());
  assert.match(result.aef.limitations.join(" "), /retrieved/);
});
