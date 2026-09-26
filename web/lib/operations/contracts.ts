import { z } from "zod";

export const SCHEMA_VERSION = "operations-v1" as const;
// Decimal parsing avoids binary floating underflow (e.g. 1.001 * 1000).
export function millimeters(value: number): number {
  const [whole, fraction = ""] = String(value).split(".");
  if (!/^\d+$/.test(whole) || !/^\d{0,3}$/.test(fraction)) throw new Error("Dimensions must be exact whole millimetres");
  return Number(whole) * 1000 + Number(fraction.padEnd(3, "0"));
}
const dimension = (max: number) => z.number().min(.001).max(max).refine((v) => { try { millimeters(v); return true; } catch { return false; } }, "Dimensions must be exact whole millimetres");
export const PointSchema = z.object({ lat: z.number().finite().min(-90).max(90), lon: z.number().finite().min(-180).max(180) }).strict();
export type Point = z.infer<typeof PointSchema>;
export const HazmatSchema = z.enum(["EXPLOSIVES", "GASES", "FLAMMABLE", "COMBUSTIBLE", "ORGANIC", "POISON", "CORROSIVE", "ASPIRATION_HAZARD", "ENVIRONMENTAL_HAZARD", "OTHER"]);
export const RouteRequestSchema = z.object({
  origin: PointSchema, destination: PointSchema,
  departure_at: z.iso.datetime({ offset: true }),
  truck: z.object({
    height_m: dimension(10), width_m: dimension(10), length_m: dimension(100),
    gross_weight_kg: z.number().int().min(1).max(500000), axle_count: z.number().int().min(2).max(50),
    trailers: z.array(z.object({ length_m: dimension(50) }).strict()).max(5),
    hazmat: z.array(HazmatSchema).max(10).refine((v) => new Set(v).size === v.length, "Duplicate hazardous goods"),
  }).strict().refine((v) => v.trailers.reduce((n, t) => n + t.length_m, 0) < v.length_m, "Trailer lengths must fit combined vehicle length"),
}).strict();
export type RouteRequest = z.infer<typeof RouteRequestSchema>;
export const SiteRequestSchema = PointSchema.extend({ year: z.number().int().min(2017).max(2100) }).strict();
export type SiteRequest = z.infer<typeof SiteRequestSchema>;
export const StatusSchema = z.enum(["available", "partial", "stale", "unavailable", "out_of_coverage", "not_configured", "deferred"]);
export type Status = z.infer<typeof StatusSchema>;
export const EnvelopeSchema = z.object({
  schema_version: z.literal(SCHEMA_VERSION), provider: z.string(), status: StatusSchema, request_hash: z.string(),
  retrieved_at: z.iso.datetime(), source_updated_at: z.iso.datetime({ offset: true }).nullable(),
  valid_from: z.iso.datetime({ offset: true }).nullable(), valid_to: z.iso.datetime({ offset: true }).nullable(),
  source_url: z.string().url(), source_version: z.string().nullable(), evidence_hash: z.string().nullable(),
  coverage: z.object({ requested: z.number().int().nonnegative(), completed: z.number().int().nonnegative(), failed: z.number().int().nonnegative(), truncated: z.boolean() }).strict(),
  data: z.unknown().nullable(), limitations: z.array(z.string()),
}).strict();
export type Envelope<T> = Omit<z.infer<typeof EnvelopeSchema>, "data"> & { data: T | null };
export type ForecastPeriod = { start: string; end: string; temperature: number | null; temperature_unit: string | null; wind_speed: string | null; wind_direction: string | null; precipitation_probability: number | null; description: string };
export type WeatherAlert = { id: string; event: string; severity: string | null; certainty: string | null; urgency: string | null; onset: string | null; expires: string; description: string; geometry_available: boolean; affected_zones: string[] };
export type WeatherData = { samples: { point: Point; forecast: ForecastPeriod[]; alerts: WeatherAlert[]; updated_at: string; alerts_checked_at: string; alert_coverage: "point_county_and_zone" }[]; scope: string };
export type SoilData = { map_units: { mukey: string; name: string; area_symbol: string; survey_updated_at: string | null; components: { cokey: string; name: string | null; percent: number | null; drainage_class: string | null; hydrologic_group: string | null }[] }[]; scope: string };
export type RoadworkData = { jurisdictions: string[]; events: { id: string; road_names: string[]; direction: string; start: string; end: string; vehicle_impact: string; description: string | null; event_status: string | null; start_verified: boolean | null; end_verified: boolean | null; source_updated_at: string | null; restrictions: { type: string; value: number | null; unit: string | null }[] }[]; scope: string };
export type AEFSample = { point: Point; year: number; object_url: string; object_etag: string; index_sha256: string; sample_sha256: string; crs: string; row: number; col: number; pixel_size_m: number; raw: number[]; embedding: number[]; attribution: string };
export type AEFData = { samples: AEFSample[]; scope: "annual_satellite_embedding" };
export type RouteData = { distance_m: number; travel_seconds: number; eta: string; restrictions_partially_ignored: boolean; warnings: string[]; attribution: "Google Maps" };
export type SiteResponse = { request: SiteRequest; weather: Envelope<WeatherData>; soil: Envelope<SoilData>; aef: Envelope<AEFData>; roadwork: Envelope<RoadworkData> };
export type RouteResponse = { request: RouteRequest; status: "complete" | "incomplete"; route: Envelope<RouteData>; weather: Envelope<WeatherData>; roadwork: Envelope<RoadworkData>; aef: Envelope<AEFData>; limitations: string[] };
export type ReferenceResponse = { schema_version: typeof SCHEMA_VERSION; aef_years: number[]; providers: { id: string; ready: boolean; jurisdictions: string[]; refresh_seconds: number | null; attribution: string; reason: string | null }[]; hazmat: string[]; limits: { route_samples: number; route_sample_max_gap_km: number; max_departure_days: number }; };

export function parseSiteQuery(params: URLSearchParams): SiteRequest {
  const keys = ["lat", "lon", "year"];
  for (const key of params.keys()) if (!keys.includes(key) || params.getAll(key).length !== 1) throw new Error("Unknown or duplicate parameter");
  const number = (key: string) => { const value = params.get(key); if (!value || !/^-?\d+(\.\d+)?$/.test(value)) throw new Error(`Invalid ${key}`); return Number(value); };
  return SiteRequestSchema.parse({ lat: number("lat"), lon: number("lon"), year: number("year") });
}
