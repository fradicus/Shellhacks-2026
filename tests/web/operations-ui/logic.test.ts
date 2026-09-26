import assert from "node:assert/strict";
import test from "node:test";
import {
  ConditionsResponseSchema,
  OutcomeStatusSchema,
  PredictionResponseSchema,
  RequestEpoch,
  SiteResponseSchema,
  VisibilityPoller,
  buildOutcomeRequest,
  buildRouteRequest,
  buildSiteRequest,
  claimAttempt,
  conditionsInterval,
  directoryBinding,
  pointBinding,
  readResponse,
  siteBinding,
  type PollScheduler,
} from "../../../web/components/operations/logic.ts";

const stamp = "2026-09-26T16:00:00Z";
const sources: Record<string, string> = { weather: "https://api.weather.gov", soil: "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
  roadwork: "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed", route: "https://routes.googleapis.com/directions/v2:computeRoutes",
  aef: "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL" };
const base = (provider: string, status: string, data: unknown) => ({
  schema_version: "operations-v1", provider, status, request_hash: "request", retrieved_at: stamp,
  source_updated_at: null, valid_from: null, valid_to: null, source_url: sources[provider],
  source_version: null, evidence_hash: null, coverage: { requested: 1, completed: data ? 1 : 0, failed: data ? 0 : 1, truncated: false },
  data, limitations: data ? ["Synthetic test-only provider response."] : ["Synthetic unavailable state."],
});
const weatherData = { scope: "synthetic point", samples: [{
  point: { lat: 47.6, lon: -122.3 }, updated_at: stamp, alerts_checked_at: stamp, alert_coverage: "point_county_and_zone",
  forecast: [{ start: stamp, end: "2026-09-26T17:00:00Z", temperature: null, temperature_unit: null, wind_speed: null, wind_direction: null, precipitation_probability: null, description: "Synthetic test-only forecast" }],
  alerts: [],
}] };

test("manual worksite and vehicle builders require explicit facts and preserve exact units", () => {
  const site = buildSiteRequest({ label: "  Test yard  ", lat: "47.6", lon: "-122.3", year: "2025" });
  assert.deepEqual(site, { label: "Test yard", request: { lat: 47.6, lon: -122.3, year: 2025 } });
  assert.throws(() => buildSiteRequest({ label: "", lat: "47.6", lon: "-122.3", year: "2025" }), /label/);
  const draft = { originLabel: "Depot", originLat: "47.5", originLon: "-122.2", departureLocal: "2026-09-26T12:00",
    heightM: "4.101", widthM: "2.59", lengthM: "18", grossWeightKg: "36000", axleCount: "5",
    trailerMode: "none" as const, trailers: [], hazmatReviewed: true, hazmat: [] };
  const route = buildRouteRequest(draft, { lat: 47.6, lon: -122.3 });
  assert.equal(route.truck.height_m, 4.101); assert.equal(route.truck.gross_weight_kg, 36000); assert.deepEqual(route.truck.trailers, []);
  assert.throws(() => buildRouteRequest({ ...draft, heightM: "4.1008" }, route.destination), /millimetres/);
  assert.throws(() => buildRouteRequest({ ...draft, hazmatReviewed: false }, route.destination), /hazardous/);
  assert.throws(() => buildRouteRequest({ ...draft, trailerMode: "" }, route.destination), /trailers/);
});

test("outcome requests require an explicit as-of baseline confirmation", () => {
  const draft = { jobType: "substation", companyId: "company-1", region: "northwest", asOfLocal: "2026-09-26T12:00", plannedDurationDays: "90", baselineConfirmed: false };
  assert.throws(() => buildOutcomeRequest(draft), /confirmation/);
  const built = buildOutcomeRequest({ ...draft, baselineConfirmed: true });
  assert.equal(built.planned_duration_days, 90); assert.equal(built.planned_duration_confirmed_at_as_of, true); assert.match(built.as_of, /Z$/);
});

test("local datetime validation rejects a daylight-saving gap instead of normalizing it", () => {
  const previous = process.env.TZ;
  process.env.TZ = "America/New_York";
  try {
    assert.throws(() => buildOutcomeRequest({ jobType: "substation", companyId: "company-1", region: "northeast",
      asOfLocal: "2026-03-08T02:30", plannedDurationDays: "", baselineConfirmed: false }), /does not exist/);
  } finally {
    if (previous === undefined) delete process.env.TZ; else process.env.TZ = previous;
  }
});

test("strict response validation keeps mixed provider states and checks request binding", () => {
  const conditions = ConditionsResponseSchema.parse({ request: { lat: 47.6, lon: -122.3 }, weather: base("weather", "available", weatherData), roadwork: base("roadwork", "out_of_coverage", null) });
  assert.equal(conditions.weather.status, "available"); assert.equal(conditions.roadwork.status, "out_of_coverage");
  assert.equal(pointBinding(conditions, { lat: 47.6, lon: -122.3 }), true);
  assert.equal(pointBinding(conditions, { lat: 47.61, lon: -122.3 }), false);
  const mismatchedWeather = ConditionsResponseSchema.parse({ ...conditions, weather: { ...conditions.weather, data: {
    ...conditions.weather.data!, samples: [{ ...conditions.weather.data!.samples[0], point: { lat: 47.61, lon: -122.3 } }],
  } } });
  assert.equal(pointBinding(mismatchedWeather, { lat: 47.6, lon: -122.3 }), false);
  const site = SiteResponseSchema.parse({ request: { lat: 47.6, lon: -122.3, year: 2025 }, weather: conditions.weather,
    roadwork: conditions.roadwork, soil: base("soil", "unavailable", null), aef: base("aef", "unavailable", null) });
  assert.equal(siteBinding(site, site.request), true);
  const aef = base("aef", "available", { scope: "annual_satellite_embedding", samples: [{ point: { lat: 47.6, lon: -122.3 }, year: 2024,
    object_url: "https://example.test/synthetic-aef", object_etag: "synthetic", index_sha256: "a".repeat(64), sample_sha256: "b".repeat(64),
    crs: "EPSG:4326", row: 1, col: 1, pixel_size_m: 10, raw: Array(64).fill(0), embedding: Array(64).fill(0), attribution: "Synthetic test only" }] });
  const wrongYearSite = SiteResponseSchema.parse({ ...site, aef });
  assert.equal(siteBinding(wrongYearSite, site.request), false);
  assert.equal(SiteResponseSchema.safeParse({ ...site, extra: true }).success, false);
  assert.equal(ConditionsResponseSchema.safeParse({ ...conditions, weather: { ...conditions.weather, data: { benign: true } } }).success, false);
  assert.equal(ConditionsResponseSchema.safeParse({ ...conditions, weather: { ...conditions.weather, status: "unavailable" } }).success, false);
  assert.equal(ConditionsResponseSchema.safeParse({ ...conditions, weather: { ...conditions.weather, data: null } }).success, false);
  assert.equal(ConditionsResponseSchema.safeParse({ ...conditions, weather: { ...conditions.weather, source_url: "javascript:alert(1)" } }).success, false);
  assert.equal(ConditionsResponseSchema.safeParse({ ...conditions, weather: { ...conditions.weather, coverage: { ...conditions.weather.coverage, completed: 2 } } }).success, false);
});

test("unavailable actual-history payload cannot contain a numerical prediction", () => {
  const unavailable = PredictionResponseSchema.parse({ status: "unavailable", reason: "No approved model", request: null, prediction: null,
    support: null, evaluation: null, model_version: null, limitations: ["Synthetic unavailable state."], probability_evidence: null });
  assert.equal(unavailable.prediction, null);
  assert.equal(PredictionResponseSchema.safeParse({ ...unavailable, prediction: { duration_days: { lower: 1, median: 2, upper: 3 }, delay_probability: 0.5 } }).success, false);
  assert.equal(PredictionResponseSchema.safeParse({ ...unavailable, status: "predicted", prediction: { duration_days: { lower: 1, median: 2, upper: 3 }, delay_probability: null } }).success, false);
  const status = OutcomeStatusSchema.parse({ status: "unavailable", reason: "No approved model", model_version: null, support: null, evaluation: null, limitations: [] });
  assert.equal(status.status, "unavailable");
});

test("typed unavailable responses survive HTTP status while malformed payloads fail", async () => {
  const payload = { status: "unavailable", reason: "No approved model", model_version: null, support: null, evaluation: null, limitations: [] };
  assert.equal((await readResponse(new Response(JSON.stringify(payload), { status: 503 }), OutcomeStatusSchema)).reason, "No approved model");
  await assert.rejects(() => readResponse(new Response("not json", { status: 502 }), OutcomeStatusSchema), /malformed JSON/);
  const usable = { request: { lat: 47.6, lon: -122.3 }, weather: base("weather", "available", weatherData), roadwork: base("roadwork", "out_of_coverage", null) };
  await assert.rejects(() => readResponse(new Response(JSON.stringify(usable), { status: 500 }), ConditionsResponseSchema), /usable evidence with HTTP 500/);
});

test("request epochs abort stale work and never let an older response become current", () => {
  const lane = new RequestEpoch(); const first = lane.begin(); const second = lane.begin();
  assert.equal(first.signal.aborted, true); assert.equal(first.current(), false); assert.equal(second.current(), true);
  lane.invalidate(); assert.equal(second.signal.aborted, true); assert.equal(second.current(), false);
});

test("visibility poller suspends, resumes one timer, and tears down", async () => {
  let next = 1; const callbacks = new Map<number, () => void>(); const cleared: number[] = []; const runs: string[] = [];
  const timers: PollScheduler = {
    set(callback) { const id = next++; callbacks.set(id, callback); return id as unknown as ReturnType<typeof setTimeout>; },
    clear(timer) { const id = timer as unknown as number; callbacks.delete(id); cleared.push(id); },
  };
  const poller = new VisibilityPoller(60_000, async (key) => { runs.push(key); }, timers);
  poller.bind("47.6,-122.3"); assert.equal(callbacks.size, 1);
  poller.setVisible(false); assert.equal(callbacks.size, 0); assert.equal(cleared.length, 1);
  poller.setVisible(true); assert.equal(callbacks.size, 1);
  const callback = [...callbacks.values()][0]; callbacks.clear(); callback(); await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(runs, ["47.6,-122.3"]); assert.equal(callbacks.size, 1);
  poller.stop(); assert.equal(callbacks.size, 0);
});

test("conditions cadence cannot be faster than either published current provider interval", () => {
  assert.equal(conditionsInterval(null), 60_000);
  assert.equal(conditionsInterval({ schema_version: "operations-v1", aef_years: [], hazmat: [], limits: { route_samples: 5, route_sample_max_gap_km: 25, max_departure_days: 7 }, providers: [
    { id: "weather", ready: true, jurisdictions: [], refresh_seconds: 60, attribution: "NWS", reason: null },
    { id: "roadwork", ready: true, jurisdictions: [], refresh_seconds: 90, attribution: "WSDOT", reason: null },
    { id: "soil", ready: true, jurisdictions: [], refresh_seconds: 86400, attribution: "USDA", reason: null },
  ] }), 90_000);
});

test("manual and automatic condition refreshes share one per-point attempt clock", () => {
  const attempts = new Map<string, number>();
  assert.equal(claimAttempt(attempts, "point-a", 60_000, 1_000), 61_000);
  assert.equal(claimAttempt(attempts, "point-a", 60_000, 60_999), null);
  assert.equal(claimAttempt(attempts, "point-a", 60_000, 61_000), 121_000);
  assert.equal(claimAttempt(attempts, "point-b", 60_000, 61_001), 121_001);
});

test("directory results must echo the submitted literal query and fixed first page", () => {
  const response = {
    available: true, reason: null, dataset: "synthetic-test-only", generated_at: stamp,
    filters: { q: "Seattle City Light", page: 1, limit: 10 }, total: 0, page: 1, limit: 10, records: [],
  };
  assert.equal(directoryBinding(response, " Seattle City Light "), true);
  assert.equal(directoryBinding({ ...response, filters: { ...response.filters, q: "Tacoma" } }, "Seattle City Light"), false);
  assert.equal(directoryBinding({ ...response, page: 2 }, "Seattle City Light"), false);
  assert.equal(directoryBinding({ ...response, filters: { ...response.filters, state: "53" } }, "Seattle City Light"), false);
});
