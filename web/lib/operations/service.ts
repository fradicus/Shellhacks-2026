import { HazmatSchema, SCHEMA_VERSION, PointSchema, type Envelope, type Point, type RouteRequest, type RouteResponse, type SiteRequest, type SiteResponse, type ReferenceResponse, type WeatherData, type RoadworkData, type AEFData } from "./contracts";
import { aef, readSnapshot, type AEFSnapshot, ATTRIBUTION } from "./aef";
import { context, empty, weather, soil, roadwork, truckRoute } from "./providers";
import { digest } from "./transport";

export const LIMITS = { route_samples: 5, route_sample_max_gap_km: 25, max_departure_days: 7 };
export async function reference(ctx = context()): Promise<ReferenceResponse> {
  const snapshot = await readSnapshot();
  return { schema_version: SCHEMA_VERSION, aef_years: [...new Set(snapshot?.records.map((r) => r.year) ?? [])].sort(), hazmat: HazmatSchema.options, limits: LIMITS, providers: [
    { id: "weather", ready: !!ctx.userAgent, jurisdictions: ["NWS point/grid forecast coverage"], refresh_seconds: 60, attribution: "NOAA National Weather Service", reason: ctx.userAgent ? null : "NWS_USER_AGENT is not configured" },
    { id: "soil", ready: true, jurisdictions: ["USDA SSURGO surveyed coverage"], refresh_seconds: 86400, attribution: "USDA NRCS", reason: "Runtime availability and map-unit coverage require a successful query" },
    { id: "roadwork", ready: true, jurisdictions: ["WSDOT reported work zones"], refresh_seconds: 60, attribution: "Washington State Department of Transportation", reason: "Partial network coverage; not a nationwide closure service" },
    { id: "aef", ready: !!snapshot?.records.length, jurisdictions: ["Exact evidenced point/year artifacts only"], refresh_seconds: null, attribution: ATTRIBUTION, reason: snapshot?.records.length ? null : "No validated AEF point artifacts" },
    { id: "route", ready: !!ctx.googleKey && !!ctx.lvrEnabled, jurisdictions: ["Contiguous 48 United States; provider restrictions apply"], refresh_seconds: null, attribution: "Google Maps", reason: "Separate LVR provisioning required; no route is guaranteed safe or legal" },
  ] };
}
// No provider result caching: fresh independent calls, with UI refresh limits published above.
export async function site(request: SiteRequest, ctx = context(), snapshot?: AEFSnapshot | null): Promise<SiteResponse> {
  const point = { lat: request.lat, lon: request.lon };
  const [w, s, r, snap] = await Promise.all([weather(point, ctx), soil(point, ctx), roadwork(point, ctx), snapshot === undefined ? readSnapshot() : snapshot]);
  return { request, weather: w, soil: s, roadwork: r, aef: aef(point, request.year, snap, ctx.now) };
}

export function decodePolyline(encoded: string): Point[] {
  let cursor = 0, lat = 0, lon = 0; const points: Point[] = [];
  function next() {
    let value = 0, shift = 0, byte = 0;
    do { if (cursor >= encoded.length || shift > 30) throw new Error("Malformed route geometry"); byte = encoded.charCodeAt(cursor++) - 63; if (byte < 0 || byte > 63) throw new Error("Malformed route geometry"); value += (byte & 31) * 2 ** shift; shift += 5; } while (byte >= 32);
    return value % 2 ? -(Math.floor(value / 2) + 1) : value / 2;
  }
  while (cursor < encoded.length) { lat += next(); lon += next(); points.push(PointSchema.parse({ lat: lat / 1e5, lon: lon / 1e5 })); if (points.length > 20000) throw new Error("Route vertex limit exceeded"); }
  if (points.length < 2) throw new Error("Route has no usable geometry"); return points;
}
export function distanceKm(a: Point, b: Point) {
  const r = Math.PI / 180; const h = Math.sin((a.lat - b.lat) * r / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin((a.lon - b.lon) * r / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}
export function sampleRoute(points: Point[]): { points: Point[]; maxGapKm: number; limited: boolean } {
  const lengths = [0]; for (let i = 1; i < points.length; i++) lengths.push(lengths[i - 1] + distanceKm(points[i - 1], points[i]));
  const total = lengths.at(-1)!; const count = Math.min(LIMITS.route_samples, Math.max(2, Math.ceil(total / LIMITS.route_sample_max_gap_km) + 1));
  const sampled: Point[] = [];
  for (let i = 0; i < count; i++) {
    const target = total * i / (count - 1); let j = 1; while (j < lengths.length - 1 && lengths[j] < target) j++;
    const fraction = lengths[j] === lengths[j - 1] ? 0 : (target - lengths[j - 1]) / (lengths[j] - lengths[j - 1]);
    sampled.push({ lat: points[j - 1].lat + fraction * (points[j].lat - points[j - 1].lat), lon: points[j - 1].lon + fraction * (points[j].lon - points[j - 1].lon) });
  }
  return { points: sampled, maxGapKm: total / (count - 1), limited: total / (count - 1) > LIMITS.route_sample_max_gap_km };
}
function combine<T>(provider: "weather" | "roadwork" | "aef", request: RouteRequest, results: Envelope<T>[], data: T | null, limited: boolean, gap: number, now: Date, binding: unknown): Envelope<T> {
  const result = empty<T>(provider, request, `Route point samples only; maximum along-route sample gap ${gap.toFixed(2)} km. Not continuous corridor coverage.`, "partial", now);
  const completed = results.filter((r) => r.status === "available").length;
  result.data = data; result.coverage = { requested: results.length, completed, failed: results.length - completed, truncated: limited };
  result.limitations.push(...new Set(results.flatMap((r) => [`Sample status: ${r.status}; retrieved ${r.retrieved_at}; source updated ${r.source_updated_at ?? "unknown"}.`, ...r.limitations])));
  const times = results.map((r) => r.source_updated_at).filter((t): t is string => !!t).sort((a, b) => Date.parse(a) - Date.parse(b));
  result.source_updated_at = times[0] ?? null;
  result.evidence_hash = digest({ binding, samples: results.map((r) => ({ request_hash: r.request_hash, evidence_hash: r.evidence_hash, status: r.status, retrieved_at: r.retrieved_at })) });
  result.retrieved_at = results.filter((r) => r.data !== null).map((r) => r.retrieved_at).sort((a, b) => Date.parse(b) - Date.parse(a))[0] ?? now.toISOString();
  if (!data) result.status = "unavailable";
  else if (results.some((r) => r.status === "stale")) result.status = "stale";
  // Route sampling always remains partial: even closely spaced points can miss a narrow hazard.
  return result;
}
export async function route(request: RouteRequest, ctx = context(), snapshot?: AEFSnapshot | null): Promise<RouteResponse> {
  const delta = Date.parse(request.departure_at) - ctx.now.getTime();
  if (delta < -60000 || delta > LIMITS.max_departure_days * 86400_000) throw new Error("Departure must be now through seven days ahead");
  const unavailable = (provider: "weather" | "roadwork" | "aef") => empty<never>(provider, request, "No validated truck route geometry is available for sampling.", "unavailable", ctx.now);
  const { result, polyline } = await truckRoute(request, ctx);
  const response: RouteResponse = { request, status: "incomplete", route: result, weather: unavailable("weather"), roadwork: unavailable("roadwork"), aef: unavailable("aef"), limitations: ["Point samples cannot certify continuous corridor conditions or legal vehicle access."] };
  if (!polyline) return response;
  try {
    const points = decodePolyline(polyline);
    const originSnap = distanceKm(points[0], request.origin), destinationSnap = distanceKm(points.at(-1)!, request.destination);
    if (originSnap > .1 || destinationSnap > .1) throw new Error("Route endpoints differ by more than 100m from request");
    response.limitations.push(`Provider road snapping: origin ${(originSnap * 1000).toFixed(1)}m; destination ${(destinationSnap * 1000).toFixed(1)}m.`);
    response.limitations.push("Environmental samples are not resolved to per-point arrival times; departure is retained for context only. Assessment remains incomplete.");
    const sampling = sampleRoute(points); const snap = snapshot === undefined ? await readSnapshot() : snapshot;
    const binding = { route_request_hash: result.request_hash, route_evidence_hash: result.evidence_hash, route_retrieved_at: result.retrieved_at, geometry_sha256: digest(polyline), points: sampling.points, departure_at: request.departure_at, temporal_scope: "not_arrival_time_resolved" };
    const year = snap?.records.length ? Math.max(...snap.records.map((r) => r.year)) : ctx.now.getUTCFullYear() - 1;
    const results = await Promise.all(sampling.points.map(async (point) => ({ w: await weather(point, ctx), r: await roadwork(point, ctx), a: aef(point, year, snap, ctx.now) })));
    const weatherSamples = results.flatMap((r) => r.w.data?.samples ?? []);
    const zones = results.flatMap((r) => r.r.data?.events ?? []);
    const aefSamples = results.flatMap((r) => r.a.data?.samples ?? []);
    response.weather = combine<WeatherData>("weather", request, results.map((r) => r.w), weatherSamples.length ? { samples: weatherSamples, scope: "sampled route points; NOT resolved to arrival time" } : null, sampling.limited, sampling.maxGapKm, ctx.now, binding);
    response.roadwork = combine<RoadworkData>("roadwork", request, results.map((r) => r.r), results.some((r) => r.r.data) ? { events: [...new Map(zones.map((z) => [z.id, z])).values()], jurisdictions: ["WSDOT reported network only"], scope: "vicinities of sampled route points only; NOT resolved to arrival time" } : null, sampling.limited, sampling.maxGapKm, ctx.now, binding);
    response.aef = combine<AEFData>("aef", request, results.map((r) => r.a), aefSamples.length ? { samples: aefSamples, scope: "annual_satellite_embedding" } : null, sampling.limited, sampling.maxGapKm, ctx.now, binding);
    return response;
  } catch { response.limitations.push("Route geometry was invalid or could not be sampled; environmental assessment unavailable."); return response; }
}
