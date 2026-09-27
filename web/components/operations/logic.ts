import { z } from "zod";
import type {
  Envelope,
  AEFData,
  Point,
  ReferenceResponse,
  RoadworkData,
  RouteData,
  RouteRequest,
  SiteRequest,
  SoilData,
  WaterData,
  WeatherData,
} from "../../lib/operations/contracts";
import type { VerifiedCoverageResponse, VerifiedListResponse } from "../../lib/verified/types";
import type { PredictionResponse } from "../../lib/outcomes/model";

const stamp = z.string().datetime({ offset: true });
const sha = z.string().regex(/^[0-9a-f]{64}$/);
const providerSources = {
  weather: "https://api.weather.gov",
  soil: "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
  roadwork: "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed",
  route: "https://routes.googleapis.com/directions/v2:computeRoutes",
  aef: "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL",
  water: "https://waterservices.usgs.gov/nwis/iv/",
} as const;
const PointSchema = z.object({ lat: z.number().finite().min(-90).max(90), lon: z.number().finite().min(-180).max(180) }).strict();
function millimeters(value: number): number {
  const [whole, fraction = ""] = String(value).split(".");
  if (!/^\d+$/.test(whole) || !/^\d{0,3}$/.test(fraction)) throw new Error("Dimensions must be exact whole millimetres");
  return Number(whole) * 1000 + Number(fraction.padEnd(3, "0"));
}
const dimension = (max: number) => z.number().min(.001).max(max).refine((value) => { try { millimeters(value); return true; } catch { return false; } }, "Dimensions must be exact whole millimetres");
const HazmatSchema = z.enum(["EXPLOSIVES", "GASES", "FLAMMABLE", "COMBUSTIBLE", "ORGANIC", "POISON", "CORROSIVE", "ASPIRATION_HAZARD", "ENVIRONMENTAL_HAZARD", "OTHER"]);
const RouteRequestSchema = z.object({
  origin: PointSchema, destination: PointSchema, departure_at: stamp,
  truck: z.object({
    height_m: dimension(10), width_m: dimension(10), length_m: dimension(100), gross_weight_kg: z.number().int().min(1).max(500000),
    axle_count: z.number().int().min(2).max(50), trailers: z.array(z.object({ length_m: dimension(50) }).strict()).max(5),
    hazmat: z.array(HazmatSchema).max(10).refine((values) => new Set(values).size === values.length, "Duplicate hazardous goods"),
  }).strict().refine((value) => value.trailers.reduce((total, trailer) => total + trailer.length_m, 0) < value.length_m, "Trailer lengths must fit combined vehicle length"),
}).strict();
const SiteRequestSchema = PointSchema.extend({ year: z.number().int().min(2017).max(2100) }).strict();
const EnvelopeSchema = z.object({
  schema_version: z.literal("operations-v1"), provider: z.string(), status: z.enum(["available", "partial", "stale", "unavailable", "out_of_coverage", "not_configured", "deferred"]),
  request_hash: z.string(), retrieved_at: stamp, source_updated_at: stamp.nullable(), valid_from: stamp.nullable(), valid_to: stamp.nullable(),
  source_url: z.string().url(), source_version: z.string().nullable(), evidence_hash: z.string().nullable(),
  coverage: z.object({ requested: z.number().int().nonnegative(), completed: z.number().int().nonnegative(), failed: z.number().int().nonnegative(), truncated: z.boolean() }).strict(),
  data: z.unknown().nullable(), limitations: z.array(z.string()),
}).strict();

const ForecastPeriodSchema = z.object({
  start: stamp,
  end: stamp,
  temperature: z.number().finite().nullable(),
  temperature_unit: z.string().nullable(),
  wind_speed: z.string().nullable(),
  wind_direction: z.string().nullable(),
  precipitation_probability: z.number().finite().nullable(),
  description: z.string(),
}).strict();
const WeatherAlertSchema = z.object({
  id: z.string(), event: z.string(), severity: z.string().nullable(), certainty: z.string().nullable(), urgency: z.string().nullable(),
  onset: stamp.nullable(), expires: stamp, description: z.string(), geometry_available: z.boolean(), affected_zones: z.array(z.string()),
}).strict();
const WeatherDataSchema: z.ZodType<WeatherData> = z.object({
  samples: z.array(z.object({
    point: PointSchema, forecast: z.array(ForecastPeriodSchema), alerts: z.array(WeatherAlertSchema), updated_at: stamp,
    alerts_checked_at: stamp, alert_coverage: z.literal("point_county_and_zone"),
  }).strict()),
  scope: z.string(),
}).strict();
const SoilHorizonSchema = z.object({
  chkey: z.string(),
  depth_top_cm: z.number().finite().nullable(),
  depth_bottom_cm: z.number().finite().nullable(),
  ph_h2o_1_to_1: z.number().finite().nullable(),
  ph_method: z.literal("1:1 soil-water"),
  depth_unit: z.literal("cm"),
}).strict();
const SoilDataSchema: z.ZodType<SoilData> = z.object({
  map_units: z.array(z.object({
    mukey: z.string(), name: z.string(), area_symbol: z.string(), survey_updated_at: z.string().nullable(),
    components: z.array(z.object({
      cokey: z.string(), name: z.string().nullable(), percent: z.number().finite().nullable(),
      drainage_class: z.string().nullable(), hydrologic_group: z.string().nullable(),
      horizons: z.array(SoilHorizonSchema).optional(),
    }).strict()),
  }).strict()),
  scope: z.string(),
}).strict();
const RoadworkDataSchema: z.ZodType<RoadworkData> = z.object({
  jurisdictions: z.array(z.string()),
  scope: z.string(),
  events: z.array(z.object({
    id: z.string(), road_names: z.array(z.string()), direction: z.string(), start: stamp, end: stamp,
    vehicle_impact: z.string(), description: z.string().nullable(), event_status: z.string().nullable(),
    start_verified: z.boolean().nullable(), end_verified: z.boolean().nullable(), source_updated_at: stamp.nullable(),
    restrictions: z.array(z.object({ type: z.string(), value: z.number().finite().nullable(), unit: z.string().nullable() }).strict()),
  }).strict()),
}).strict();
const AEFSampleSchema = z.object({
  point: PointSchema, year: z.number().int(), object_url: z.string().url(), object_etag: z.string(), index_sha256: sha,
  sample_sha256: sha, crs: z.string(), row: z.number().int().nonnegative(), col: z.number().int().nonnegative(),
  pixel_size_m: z.number().positive(), raw: z.array(z.number().int()).length(64), embedding: z.array(z.number().finite()).length(64), attribution: z.string(),
}).strict();
const AEFDataSchema: z.ZodType<AEFData> = z.object({ samples: z.array(AEFSampleSchema), scope: z.literal("annual_satellite_embedding") }).strict();
const RouteDataSchema: z.ZodType<RouteData> = z.object({
  distance_m: z.number().finite().nonnegative(), travel_seconds: z.number().finite().nonnegative(), eta: stamp,
  restrictions_partially_ignored: z.boolean(), warnings: z.array(z.string()), attribution: z.literal("Google Maps"),
}).strict();
const WaterDataSchema: z.ZodType<WaterData> = z.object({
  rivers: z.object({
    search_radius_mi: z.number().finite().positive(),
    gauges: z.array(z.object({
      site_id: z.string(), name: z.string(), lat: z.number().finite(), lon: z.number().finite(), distance_mi: z.number().finite(),
      parameter: z.string(), parameter_name: z.string(), unit: z.string(), value: z.number().finite().nullable(), observed_at: stamp,
    }).strict()),
    scope: z.string(),
  }).strict().nullable(),
  tides: z.object({
    search_radius_mi: z.number().finite().positive(),
    station: z.object({
      id: z.string(), name: z.string(), lat: z.number().finite(), lon: z.number().finite(),
      state: z.string().nullable(), distance_mi: z.number().finite(),
    }).strict().nullable(),
    highs_lows: z.array(z.object({
      time: stamp, value_ft: z.number().finite().nullable(), type: z.enum(["high", "low"]),
    }).strict()),
    scope: z.string(),
  }).strict().nullable(),
  flood: z.object({
    zones: z.array(z.object({
      zone: z.string().nullable(), subtype: z.string().nullable(), special_flood_hazard_area: z.boolean().nullable(),
    }).strict()),
    scope: z.string(),
  }).strict().nullable(),
  wetlands: z.object({
    mapped: z.boolean(),
    features: z.array(z.object({
      wetland_type: z.string().nullable(), attribute: z.string().nullable(), acres: z.number().finite().nullable(),
    }).strict()),
    scope: z.string(),
  }).strict().nullable(),
  scope: z.string(),
}).strict();

function envelope<T>(provider: keyof typeof providerSources, data: z.ZodType<T>) {
  return EnvelopeSchema.extend({ provider: z.literal(provider), data: data.nullable() }).superRefine((value, context) => {
    if (value.source_url !== providerSources[provider]) {
      context.addIssue({ code: "custom", path: ["source_url"], message: "Source URL must match the credential-free HTTPS provider resource." });
    }
    const noData = value.status === "unavailable" || value.status === "out_of_coverage" || value.status === "not_configured" || value.status === "deferred";
    if (value.status === "available" && value.data === null) context.addIssue({ code: "custom", path: ["data"], message: "Available evidence must include data." });
    if (noData && value.data !== null) context.addIssue({ code: "custom", path: ["data"], message: `${value.status} evidence cannot include usable data.` });
    if (value.data === null && value.coverage.completed !== 0) context.addIssue({ code: "custom", path: ["coverage", "completed"], message: "Evidence without data cannot report completed coverage." });
    if (value.coverage.completed + value.coverage.failed !== value.coverage.requested) {
      context.addIssue({ code: "custom", path: ["coverage"], message: "Completed and failed coverage must equal requested checks." });
    }
    if (value.coverage.truncated && value.status === "available") context.addIssue({ code: "custom", path: ["status"], message: "Truncated evidence cannot be marked available." });
  });
}
export const WeatherEnvelopeSchema = envelope("weather", WeatherDataSchema);
export const SoilEnvelopeSchema = envelope("soil", SoilDataSchema);
export const RoadworkEnvelopeSchema = envelope("roadwork", RoadworkDataSchema);
export const AEFEnvelopeSchema = envelope("aef", AEFDataSchema);
export const RouteEnvelopeSchema = envelope("route", RouteDataSchema);
export const WaterEnvelopeSchema = envelope("water", WaterDataSchema);

export const WaterResponseSchema = z.object({
  request: PointSchema,
  water: WaterEnvelopeSchema,
}).strict();

export const SiteResponseSchema = z.object({
  request: SiteRequestSchema,
  weather: WeatherEnvelopeSchema,
  soil: SoilEnvelopeSchema,
  aef: AEFEnvelopeSchema,
  roadwork: RoadworkEnvelopeSchema,
}).strict();
export const ConditionsResponseSchema = z.object({
  request: PointSchema,
  weather: WeatherEnvelopeSchema,
  roadwork: RoadworkEnvelopeSchema,
}).strict();
export const RouteResponseSchema = z.object({
  request: RouteRequestSchema,
  status: z.enum(["complete", "incomplete"]),
  route: RouteEnvelopeSchema,
  weather: WeatherEnvelopeSchema,
  roadwork: RoadworkEnvelopeSchema,
  aef: AEFEnvelopeSchema,
  limitations: z.array(z.string()),
}).strict();
export const ReferenceResponseSchema: z.ZodType<ReferenceResponse> = z.object({
  schema_version: z.literal("operations-v1"), aef_years: z.array(z.number().int()), hazmat: z.array(HazmatSchema),
  limits: z.object({ route_samples: z.number().int().positive(), route_sample_max_gap_km: z.number().positive(), max_departure_days: z.number().int().positive() }).strict(),
  providers: z.array(z.object({
    id: z.string(), ready: z.boolean(), jurisdictions: z.array(z.string()), refresh_seconds: z.number().int().positive().nullable(),
    attribution: z.string(), reason: z.string().nullable(),
  }).strict()),
}).strict();

const VerifiedRecordSchema = z.object({
  id: z.string(), eia_utility_id: z.string(), data_year: z.number().int(), name: z.string(), state_fips: z.array(z.string()),
  county_geoids: z.array(z.string()), source_ids: z.array(z.string()), validation_status: z.enum(["accepted", "needs_review", "rejected"]),
  limitations: z.array(z.string()),
}).strict();
const VerifiedFiltersSchema = z.object({
  state: z.string().optional(), county: z.string().optional(), q: z.string().optional(), page: z.number().int().positive(), limit: z.number().int().positive(),
}).strict();
export const VerifiedListResponseSchema: z.ZodType<VerifiedListResponse> = z.object({
  available: z.boolean(), reason: z.string().nullable(), dataset: z.string().nullable(), generated_at: stamp.nullable(), filters: VerifiedFiltersSchema,
  total: z.number().int().nonnegative(), page: z.number().int().positive(), limit: z.number().int().positive(), records: z.array(VerifiedRecordSchema),
}).strict().superRefine((value, context) => {
  if (!value.available && (value.total !== 0 || value.records.length !== 0)) {
    context.addIssue({ code: "custom", message: "Unavailable directory responses cannot carry records or a positive total." });
  }
  if (value.available && (!value.dataset || !value.generated_at || value.total < value.records.length)) {
    context.addIssue({ code: "custom", message: "Available directory responses require dataset identity and consistent counts." });
  }
});
const CoverageCountsSchema = z.object({
  sources: z.number().int().nonnegative(), utilities: z.number().int().nonnegative(), utility_activities: z.number().int().nonnegative(),
  service_territory_rows: z.number().int().nonnegative(), assertions: z.number().int().nonnegative(), quarantine: z.number().int().nonnegative(),
  utilities_by_validation_status: z.record(z.string(), z.number().int().nonnegative()), service_territory_by_validation_status: z.record(z.string(), z.number().int().nonnegative()),
  resolved_county_rows: z.number().int().nonnegative(), unresolved_county_rows: z.number().int().nonnegative(), conflicting_county_rows: z.number().int().nonnegative(),
  rejected_county_rows: z.number().int().nonnegative(), independently_corroborated_service_claims: z.literal(0), comparable_field_conflicts: z.number().int().nonnegative(),
  unknown_utility_rows: z.number().int().nonnegative(), county_identity_quarantine_rows: z.number().int().nonnegative(),
}).strict();
export const VerifiedCoverageResponseSchema: z.ZodType<VerifiedCoverageResponse> = z.object({
  available: z.boolean(), reason: z.string().nullable(), dataset: z.string().nullable(), generated_at: stamp.nullable(),
  coverage: z.object({
    schema_version: z.literal("verified-directory-v1"), dataset: z.string(), generated_at: stamp, data_year: z.literal(2024),
    source_vintages: z.record(z.string(), z.string().nullable()), counts: CoverageCountsSchema, limitations: z.array(z.string()),
  }).strict().nullable(),
}).strict().superRefine((value, context) => {
  if (value.available !== (value.coverage !== null)) context.addIssue({ code: "custom", message: "Directory availability must match coverage data." });
});

const identifier = z.string().min(1).max(120).regex(/^[A-Za-z0-9_ .:/-]+$/);
export const OutcomeRequestSchema = z.object({
  job_type: identifier, company_id: identifier, region: identifier, as_of: stamp,
  planned_duration_days: z.number().int().min(1).max(3650).optional(), planned_duration_confirmed_at_as_of: z.literal(true).optional(),
}).strict().superRefine((value, context) => {
  if ((value.planned_duration_days !== undefined) !== (value.planned_duration_confirmed_at_as_of === true)) {
    context.addIssue({ code: "custom", message: "A planned duration requires explicit as-of confirmation." });
  }
});
const OutcomeRequestResponseSchema = OutcomeRequestSchema.nullable();
const OutcomeLimitations = z.array(z.string());
export const OutcomeStatusSchema = z.object({
  status: z.enum(["ready", "insufficient_evidence", "unavailable"]), reason: z.string(), model_version: z.string().nullable(),
  support: z.object({ passing_cohorts: z.number().int().nonnegative() }).strict().nullable(),
  evaluation: z.object({ cutoff: stamp, policy: z.string() }).strict().nullable(), limitations: OutcomeLimitations,
}).strict();
export const PredictionResponseSchema: z.ZodType<PredictionResponse> = z.object({
  status: z.enum(["predicted", "insufficient_evidence", "unavailable", "invalid"]), reason: z.string(), request: OutcomeRequestResponseSchema,
  prediction: z.object({
    duration_days: z.object({ lower: z.number().finite().positive(), median: z.number().finite().positive(), upper: z.number().finite().positive() }).strict(),
    delay_probability: z.number().min(0).max(1).nullable(),
  }).strict().nullable(),
  support: z.object({ training: z.number().int().min(30), calibration: z.number().int().min(20), holdout: z.number().int().min(20) }).strict().nullable(),
  evaluation: z.object({ passed: z.literal(true), evaluated_at: stamp, mae_days: z.number().finite().nonnegative(), baseline_mae_days: z.number().finite().nonnegative(), interval_coverage: z.number().min(0).max(1) }).strict().nullable(),
  model_version: z.string().min(1).nullable(), limitations: OutcomeLimitations,
  probability_evidence: z.object({
    numerator: z.number().int().nonnegative(), denominator: z.number().int().positive(),
    interval_95: z.object({ lower: z.number().min(0).max(1), upper: z.number().min(0).max(1) }).strict(), interpretation: z.string(),
  }).strict().nullable(),
}).strict().superRefine((value, context) => {
  if ((value.status === "predicted") !== (value.prediction !== null)) {
    context.addIssue({ code: "custom", message: "Prediction values must match predicted status." });
  }
  if (value.status === "predicted" && (!value.request || !value.support || !value.evaluation || !value.model_version)) {
    context.addIssue({ code: "custom", message: "Predictions require bound request, support, evaluation and model identity." });
  }
  if (value.status !== "predicted" && (value.support || value.evaluation || value.model_version || value.probability_evidence)) {
    context.addIssue({ code: "custom", message: "Non-predictions cannot carry model results." });
  }
  if ((value.prediction?.delay_probability !== null && value.prediction?.delay_probability !== undefined) !== (value.probability_evidence !== null)) {
    context.addIssue({ code: "custom", message: "Delay probability requires its evidence counts." });
  }
  const duration = value.prediction?.duration_days;
  if (duration && !(duration.lower <= duration.median && duration.median <= duration.upper)) {
    context.addIssue({ code: "custom", path: ["prediction", "duration_days"], message: "Duration bounds must be ordered." });
  }
  const probability = value.probability_evidence;
  if (probability && (probability.numerator > probability.denominator || probability.interval_95.lower > probability.interval_95.upper
    || value.prediction?.delay_probability !== probability.numerator / probability.denominator
    || probability.denominator !== value.support?.training
    || !value.request?.planned_duration_confirmed_at_as_of)) {
    context.addIssue({ code: "custom", path: ["probability_evidence"], message: "Probability evidence must be ordered, supported and bound to the confirmed baseline." });
  }
});

export type SiteResponse = z.infer<typeof SiteResponseSchema>;
export type ConditionsResponse = z.infer<typeof ConditionsResponseSchema>;
export type WaterResponse = z.infer<typeof WaterResponseSchema>;
export type RouteResponse = z.infer<typeof RouteResponseSchema>;
export type OutcomeStatus = z.infer<typeof OutcomeStatusSchema>;

export type SiteDraft = { label: string; lat: string; lon: string; year: string };
export type RouteDraft = {
  originLabel: string; originLat: string; originLon: string; departureLocal: string;
  heightM: string; widthM: string; lengthM: string; grossWeightKg: string; axleCount: string;
  trailerMode: "" | "none" | "listed"; trailers: string[]; hazmatReviewed: boolean; hazmat: string[];
};
export type OutcomeDraft = {
  jobType: string; companyId: string; region: string; asOfLocal: string; plannedDurationDays: string; baselineConfirmed: boolean;
};

function requiredNumber(value: string, name: string): number {
  if (!value.trim() || !/^-?\d+(\.\d+)?$/.test(value.trim())) throw new Error(`${name} must be a number.`);
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${name} must be finite.`);
  return number;
}
function requiredInteger(value: string, name: string): number {
  const number = requiredNumber(value, name);
  if (!Number.isInteger(number)) throw new Error(`${name} must be a whole number.`);
  return number;
}
function localToIso(value: string, name: string): string {
  if (!value) throw new Error(`${name} is required.`);
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) throw new Error(`${name} is invalid.`);
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new Error(`${name} is invalid.`);
  const parts = match.slice(1, 6).map(Number);
  const seconds = match[6] ? Number(match[6]) : 0;
  if (date.getFullYear() !== parts[0] || date.getMonth() + 1 !== parts[1] || date.getDate() !== parts[2]
    || date.getHours() !== parts[3] || date.getMinutes() !== parts[4] || date.getSeconds() !== seconds) {
    throw new Error(`${name} does not exist in the current local time zone.`);
  }
  return date.toISOString().replace(".000Z", "Z");
}

export function buildSiteRequest(draft: SiteDraft): { label: string; request: SiteRequest } {
  const label = draft.label.trim();
  if (!label) throw new Error("Worksite label is required.");
  return { label, request: SiteRequestSchema.parse({
    lat: requiredNumber(draft.lat, "Worksite latitude"), lon: requiredNumber(draft.lon, "Worksite longitude"),
    year: requiredInteger(draft.year, "AEF year"),
  }) };
}

/** Round WGS84 degrees for form fields without inventing precision beyond map clicks. */
export function formatCoordinate(value: number): string {
  if (!Number.isFinite(value)) throw new Error("Coordinate must be finite.");
  return value.toFixed(6);
}

export function draftFromSearchParams(params: URLSearchParams): Partial<SiteDraft> {
  const next: Partial<SiteDraft> = {};
  const label = params.get("label");
  const lat = params.get("lat");
  const lon = params.get("lon");
  const year = params.get("year");
  if (label != null && label.trim()) next.label = label.trim().slice(0, 120);
  if (lat != null && /^-?\d+(\.\d+)?$/.test(lat)) next.lat = lat;
  if (lon != null && /^-?\d+(\.\d+)?$/.test(lon)) next.lon = lon;
  if (year != null && /^\d{4}$/.test(year)) next.year = year;
  return next;
}

export function buildRouteRequest(draft: RouteDraft, destination: Point): RouteRequest {
  if (!draft.originLabel.trim()) throw new Error("Origin label is required.");
  if (!draft.trailerMode) throw new Error("Confirm whether the vehicle has trailers.");
  if (!draft.hazmatReviewed) throw new Error("Confirm the hazardous-goods list, including an explicit none.");
  const trailers = draft.trailerMode === "none" ? [] : draft.trailers.map((value, index) => ({ length_m: requiredNumber(value, `Trailer ${index + 1} length`) }));
  if (draft.trailerMode === "listed" && trailers.length === 0) throw new Error("Add at least one trailer or select no trailers.");
  return RouteRequestSchema.parse({
    origin: { lat: requiredNumber(draft.originLat, "Origin latitude"), lon: requiredNumber(draft.originLon, "Origin longitude") },
    destination,
    departure_at: localToIso(draft.departureLocal, "Departure"),
    truck: {
      height_m: requiredNumber(draft.heightM, "Total height"), width_m: requiredNumber(draft.widthM, "Total width"),
      length_m: requiredNumber(draft.lengthM, "Total length"), gross_weight_kg: requiredInteger(draft.grossWeightKg, "Gross weight"),
      axle_count: requiredInteger(draft.axleCount, "Axle count"), trailers, hazmat: draft.hazmat,
    },
  });
}

export function buildOutcomeRequest(draft: OutcomeDraft): z.infer<typeof OutcomeRequestSchema> {
  const value: Record<string, unknown> = {
    job_type: draft.jobType.trim(), company_id: draft.companyId.trim(), region: draft.region.trim(), as_of: localToIso(draft.asOfLocal, "Decision as-of time"),
  };
  if (draft.plannedDurationDays.trim()) {
    value.planned_duration_days = requiredInteger(draft.plannedDurationDays, "Planned duration");
    if (draft.baselineConfirmed) value.planned_duration_confirmed_at_as_of = true;
  } else if (draft.baselineConfirmed) {
    value.planned_duration_confirmed_at_as_of = true;
  }
  return OutcomeRequestSchema.parse(value);
}

export function siteBinding(response: SiteResponse, request: SiteRequest): boolean {
  const pointMatches = (point: Point) => point.lat === request.lat && point.lon === request.lon;
  return response.request.lat === request.lat && response.request.lon === request.lon && response.request.year === request.year
    && (response.weather.data?.samples.every((sample) => pointMatches(sample.point)) ?? true)
    && (response.aef.data?.samples.every((sample) => pointMatches(sample.point) && sample.year === request.year) ?? true);
}
export function pointBinding(response: ConditionsResponse, point: Point): boolean {
  return response.request.lat === point.lat && response.request.lon === point.lon
    && (response.weather.data?.samples.every((sample) => sample.point.lat === point.lat && sample.point.lon === point.lon) ?? true);
}
export function routeBinding(response: RouteResponse, request: RouteRequest): boolean {
  return JSON.stringify(response.request) === JSON.stringify(request);
}
export function outcomeBinding(response: PredictionResponse, request: z.infer<typeof OutcomeRequestSchema>): boolean {
  return response.request !== null && JSON.stringify(response.request) === JSON.stringify(request);
}
export function directoryBinding(response: VerifiedListResponse, query: string): boolean {
  const expected = query.trim() || undefined;
  return response.page === 1 && response.limit === 10 && response.filters.page === 1 && response.filters.limit === 10 && response.filters.q === expected
    && response.filters.state === undefined && response.filters.county === undefined;
}

export async function readResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const value: unknown = await response.json().catch(() => { throw new Error("The service returned malformed JSON."); });
  const parsed = schema.safeParse(value);
  // Domain APIs use a validated unavailable payload with a non-2xx status. Preserve that reason/state.
  if (parsed.success && response.ok) return parsed.data;
  if (parsed.success) {
    const typed = parsed.data as Record<string, unknown>;
    const unavailable = typed.available === false || (typeof typed.status === "string" && ["unavailable", "insufficient_evidence", "invalid", "not_configured", "out_of_coverage", "deferred"].includes(typed.status));
    if (unavailable) return parsed.data;
    throw new Error(`The service returned usable evidence with HTTP ${response.status}; it was rejected.`);
  }
  if (!response.ok) {
    const message = typeof value === "object" && value !== null && "error" in value && typeof value.error === "string" ? value.error : `Request failed (${response.status}).`;
    throw new Error(message);
  }
  throw new Error("The service returned an unexpected response shape.");
}

export function statusTone(status: string): "ok" | "warn" | "unknown" {
  if (status === "available" || status === "ready" || status === "predicted" || status === "accepted") return "ok";
  if (status === "partial" || status === "stale" || status === "needs_review" || status === "insufficient_evidence") return "warn";
  return "unknown";
}

export function conditionsInterval(reference: ReferenceResponse | null): number {
  const seconds = reference?.providers.filter((provider) => provider.id === "weather" || provider.id === "roadwork")
    .flatMap((provider) => provider.refresh_seconds === null ? [] : [provider.refresh_seconds]) ?? [];
  return Math.max(60, ...seconds) * 1000;
}

export function claimAttempt(attempts: Map<string, number>, key: string, intervalMs: number, now = Date.now()): number | null {
  const previous = attempts.get(key);
  if (previous !== undefined && now - previous < intervalMs) return null;
  attempts.set(key, now);
  return now + intervalMs;
}

export class RequestEpoch {
  private epoch = 0;
  private controller: AbortController | null = null;
  begin() {
    this.controller?.abort();
    this.controller = new AbortController();
    const epoch = ++this.epoch;
    return { epoch, signal: this.controller.signal, current: () => epoch === this.epoch && !this.controller?.signal.aborted };
  }
  invalidate() { this.controller?.abort(); this.controller = null; this.epoch++; }
}

type Timer = ReturnType<typeof setTimeout>;
export type PollScheduler = { set: (callback: () => void, delay: number) => Timer; clear: (timer: Timer) => void };
const scheduler: PollScheduler = { set: (callback, delay) => setTimeout(callback, delay), clear: (timer) => clearTimeout(timer) };

export class VisibilityPoller {
  private timer: Timer | null = null;
  private key: string | null = null;
  private visible = true;
  private stopped = false;
  private readonly intervalMs: number;
  private readonly run: (key: string) => Promise<void>;
  private readonly timers: PollScheduler;
  constructor(intervalMs: number, run: (key: string) => Promise<void>, timers: PollScheduler = scheduler) {
    this.intervalMs = intervalMs; this.run = run; this.timers = timers;
  }
  bind(key: string) { this.stopTimer(); this.key = key; this.stopped = false; this.schedule(); }
  setVisible(visible: boolean) { this.visible = visible; this.stopTimer(); if (visible) this.schedule(); }
  stop() { this.stopped = true; this.key = null; this.stopTimer(); }
  private stopTimer() { if (this.timer !== null) this.timers.clear(this.timer); this.timer = null; }
  private schedule() {
    if (this.stopped || !this.visible || this.key === null || this.timer !== null) return;
    const key = this.key;
    this.timer = this.timers.set(() => {
      this.timer = null;
      void this.run(key).finally(() => { if (this.key === key) this.schedule(); });
    }, this.intervalMs);
  }
}

export function providerLabel(provider: string): string {
  return ({ weather: "Weather", roadwork: "Road work", soil: "Soil survey", aef: "Annual AEF context", route: "Truck route", water: "Water context" } as Record<string, string>)[provider] ?? provider;
}

export type AnyEnvelope = Envelope<WeatherData | RoadworkData | SoilData | AEFData | RouteData | WaterData>;
