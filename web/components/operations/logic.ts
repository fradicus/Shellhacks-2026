import { z } from "zod";
import {
  AEFData,
  EnvelopeSchema,
  HazmatSchema,
  PointSchema,
  RouteRequestSchema,
  SiteRequestSchema,
  type Envelope,
  type Point,
  type ReferenceResponse,
  type RoadworkData,
  type RouteData,
  type RouteRequest,
  type SiteRequest,
  type SoilData,
  type WeatherData,
} from "@/lib/operations/contracts";
import type { VerifiedCoverageResponse, VerifiedListResponse } from "@/lib/verified/types";
import type { PredictionResponse } from "@/lib/outcomes/model";

const stamp = z.string().datetime({ offset: true });
const sha = z.string().regex(/^[0-9a-f]{64}$/);

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
const SoilDataSchema: z.ZodType<SoilData> = z.object({
  map_units: z.array(z.object({
    mukey: z.string(), name: z.string(), area_symbol: z.string(), survey_updated_at: z.string().nullable(),
    components: z.array(z.object({
      cokey: z.string(), name: z.string().nullable(), percent: z.number().finite().nullable(),
      drainage_class: z.string().nullable(), hydrologic_group: z.string().nullable(),
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

function envelope<T>(provider: string, data: z.ZodType<T>) {
  return EnvelopeSchema.extend({ provider: z.literal(provider), data: data.nullable() });
}
export const WeatherEnvelopeSchema = envelope("weather", WeatherDataSchema);
export const SoilEnvelopeSchema = envelope("soil", SoilDataSchema);
export const RoadworkEnvelopeSchema = envelope("roadwork", RoadworkDataSchema);
export const AEFEnvelopeSchema = envelope("aef", AEFDataSchema);
export const RouteEnvelopeSchema = envelope("route", RouteDataSchema);

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
}).strict();
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
}).strict();

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
    duration_days: z.object({ lower: z.number().finite(), median: z.number().finite(), upper: z.number().finite() }).strict(),
    delay_probability: z.number().min(0).max(1).nullable(),
  }).strict().nullable(),
  support: z.object({ training: z.number().int().nonnegative(), calibration: z.number().int().nonnegative(), holdout: z.number().int().nonnegative() }).strict().nullable(),
  evaluation: z.object({ passed: z.literal(true), evaluated_at: stamp, mae_days: z.number().finite(), baseline_mae_days: z.number().finite(), interval_coverage: z.number().min(0).max(1) }).strict().nullable(),
  model_version: z.string().nullable(), limitations: OutcomeLimitations,
  probability_evidence: z.object({
    numerator: z.number().int().nonnegative(), denominator: z.number().int().positive(),
    interval_95: z.object({ lower: z.number().min(0).max(1), upper: z.number().min(0).max(1) }).strict(), interpretation: z.string(),
  }).strict().nullable(),
}).strict();

export type SiteResponse = z.infer<typeof SiteResponseSchema>;
export type ConditionsResponse = z.infer<typeof ConditionsResponseSchema>;
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
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new Error(`${name} is invalid.`);
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
  return response.request.lat === request.lat && response.request.lon === request.lon && response.request.year === request.year;
}
export function pointBinding(response: ConditionsResponse, point: Point): boolean {
  return response.request.lat === point.lat && response.request.lon === point.lon;
}
export function routeBinding(response: RouteResponse, request: RouteRequest): boolean {
  return JSON.stringify(response.request) === JSON.stringify(request);
}
export function outcomeBinding(response: PredictionResponse, request: z.infer<typeof OutcomeRequestSchema>): boolean {
  return response.request !== null && JSON.stringify(response.request) === JSON.stringify(request);
}

export async function readResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const value: unknown = await response.json().catch(() => { throw new Error("The service returned malformed JSON."); });
  const parsed = schema.safeParse(value);
  // Domain APIs use a validated unavailable payload with a non-2xx status. Preserve that reason/state.
  if (parsed.success) return parsed.data;
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
  constructor(private readonly intervalMs: number, private readonly run: (key: string) => Promise<void>, private readonly timers: PollScheduler = scheduler) {}
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
  return ({ weather: "Weather", roadwork: "Road work", soil: "Soil survey", aef: "Annual AEF context", route: "Truck route" } as Record<string, string>)[provider] ?? provider;
}

export type AnyEnvelope = Envelope<WeatherData | RoadworkData | SoilData | AEFData | RouteData>;
