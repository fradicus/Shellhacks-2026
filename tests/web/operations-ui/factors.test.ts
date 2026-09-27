import assert from "node:assert/strict";
import test from "node:test";
import {
  applyFactorRates,
  deriveRouteFactors,
  emptyRates,
  money,
  rateError,
} from "../../../web/components/operations/factors.ts";

const stamp = "2026-09-26T16:00:00Z";
const sources = {
  weather: "https://api.weather.gov",
  soil: "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
  roadwork: "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed",
  route: "https://routes.googleapis.com/directions/v2:computeRoutes",
  aef: "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL",
};

const envelope = (provider: keyof typeof sources, status: string, data: unknown) => ({
  schema_version: "operations-v1" as const,
  provider,
  status,
  request_hash: "request",
  retrieved_at: stamp,
  source_updated_at: null,
  valid_from: null,
  valid_to: null,
  source_url: sources[provider],
  source_version: null,
  evidence_hash: null,
  coverage: { requested: 1, completed: data ? 1 : 0, failed: data ? 0 : 1, truncated: false },
  data,
  limitations: data ? ["Synthetic test-only provider response."] : ["Synthetic unavailable state."],
});

const weather = envelope("weather", "available", {
  scope: "synthetic point",
  samples: [{
    point: { lat: 47.6, lon: -122.3 },
    updated_at: stamp,
    alerts_checked_at: stamp,
    alert_coverage: "point_county_and_zone",
    forecast: [{
      start: stamp,
      end: "2026-09-26T17:00:00Z",
      temperature: 55,
      temperature_unit: "F",
      wind_speed: "5 mph",
      wind_direction: "W",
      precipitation_probability: 80,
      description: "Synthetic rain",
    }],
    alerts: [{
      id: "alert-1",
      event: "Wind Advisory",
      severity: "Moderate",
      certainty: "Likely",
      urgency: "Expected",
      onset: stamp,
      expires: "2026-09-26T20:00:00Z",
      description: "Synthetic alert",
      geometry_available: false,
      affected_zones: [],
    }],
  }],
});

const roadwork = envelope("roadwork", "available", {
  jurisdictions: ["WA"],
  scope: "synthetic",
  events: [{
    id: "wz-1",
    road_names: ["SR 99"],
    direction: "northbound",
    start: stamp,
    end: "2026-09-27T00:00:00Z",
    vehicle_impact: "all-lanes-closed",
    description: "Synthetic closure",
    event_status: "active",
    start_verified: true,
    end_verified: false,
    source_updated_at: stamp,
    restrictions: [],
  }],
});

const soil = envelope("soil", "available", {
  scope: "synthetic",
  map_units: [{
    mukey: "1",
    name: "Synthetic loam",
    area_symbol: "WA033",
    survey_updated_at: null,
    components: [{
      cokey: "c1",
      name: "Unit",
      percent: 85,
      drainage_class: "Poorly drained",
      hydrologic_group: "D",
    }],
  }],
});

const aef = envelope("aef", "available", {
  scope: "annual_satellite_embedding",
  samples: [{
    point: { lat: 47.6, lon: -122.3 },
    year: 2025,
    object_url: "https://example.test/object",
    object_etag: "etag",
    index_sha256: "index",
    sample_sha256: "sample",
    crs: "EPSG:4326",
    row: 1,
    col: 1,
    pixel_size_m: 10,
    raw: [],
    embedding: [],
    attribution: "Synthetic AEF",
  }],
});

const site = {
  request: { lat: 47.6, lon: -122.3, year: 2025 },
  weather,
  soil,
  aef,
  roadwork,
};

const route = {
  request: {
    origin: { lat: 47.5, lon: -122.2 },
    destination: { lat: 47.6, lon: -122.3 },
    departure_at: "2026-09-26T19:00:00Z",
    truck: {
      height_m: 4.1,
      width_m: 2.5,
      length_m: 18,
      gross_weight_kg: 36000,
      axle_count: 5,
      trailers: [],
      hazmat: [],
    },
  },
  status: "complete" as const,
  route: envelope("route", "partial", {
    distance_m: 16093.44,
    travel_seconds: 3600,
    eta: "2026-09-26T20:00:00Z",
    restrictions_partially_ignored: true,
    warnings: ["Synthetic low bridge warning"],
    attribution: "Google Maps" as const,
  }),
  weather,
  roadwork,
  aef,
  limitations: ["Synthetic incomplete assessment."],
};

test("deriveRouteFactors marks present evidence without inventing minutes or costs", () => {
  const factors = deriveRouteFactors({ site, route, weather, roadwork });
  const byId = Object.fromEntries(factors.map((factor) => [factor.id, factor]));
  assert.equal(byId.travel_baseline.presence, "present");
  assert.equal(byId.travel_baseline.known_time_minutes, 60);
  assert.equal(byId.weather_alert.presence, "present");
  assert.equal(byId.precipitation.presence, "present");
  assert.equal(byId.roadwork.presence, "present");
  assert.equal(byId.route_restriction.presence, "present");
  assert.equal(byId.route_warning.presence, "present");
  assert.equal(byId.soil_drainage.presence, "present");
  assert.equal(byId.aef_coverage.presence, "present");
  assert.equal(byId.weather_alert.known_time_minutes, null);
});

test("without a route, baseline stays unknown and no minutes are invented", () => {
  const factors = deriveRouteFactors({ site, route: null, weather, roadwork });
  const baseline = factors.find((factor) => factor.id === "travel_baseline");
  assert.equal(baseline?.presence, "unknown");
  assert.equal(baseline?.known_time_minutes, null);
});

test("applyFactorRates seeds baseline travel and keeps totals null until costs are complete", () => {
  const factors = deriveRouteFactors({ site, route, weather, roadwork });
  const rates = emptyRates(factors);
  const seeded = applyFactorRates(factors, rates);
  assert.equal(seeded.factors.find((factor) => factor.id === "travel_baseline")?.time_minutes_add, 60);
  assert.equal(seeded.totals.time_minutes, null, "other present factors still need explicit minutes");
  assert.equal(seeded.totals.cost_cents, null);

  rates.travel_baseline = { time_minutes: "60", cost_usd: "120.50" };
  rates.weather_alert = { time_minutes: "30", cost_usd: "40" };
  rates.precipitation = { time_minutes: "15", cost_usd: "" };
  rates.roadwork = { time_minutes: "45", cost_usd: "80" };
  rates.route_restriction = { time_minutes: "0", cost_usd: "25" };
  rates.route_warning = { time_minutes: "10", cost_usd: "" };
  rates.soil_drainage = { time_minutes: "", cost_usd: "200" };
  rates.aef_coverage = { time_minutes: "", cost_usd: "" };

  const applied = applyFactorRates(factors, rates);
  assert.equal(applied.totals.time_minutes, 60 + 30 + 15 + 45 + 0 + 10);
  assert.equal(applied.totals.cost_cents, 12050 + 4000 + 8000 + 2500 + 20000);
  assert.equal(money(applied.totals.cost_cents!), "$465.50");
});

test("rate validation rejects negatives and oversized values without inventing zeros", () => {
  assert.equal(rateError("", false), null);
  assert.match(rateError("-1", false) ?? "", /nonnegative|whole/);
  assert.match(rateError("1.5", false) ?? "", /whole/);
  assert.match(rateError("12.345", true) ?? "", /decimals/);
  assert.equal(rateError("0", true), null);
});
