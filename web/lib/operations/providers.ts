import { z } from "zod";
import { SCHEMA_VERSION, PointSchema, RouteRequestSchema, millimeters, type Envelope, type Point, type WeatherData, type SoilData, type RoadworkData, type RouteRequest, type RouteData } from "./contracts";
import { washingtonContains } from "./jurisdiction";
import { digest, transport, type Transport } from "./transport";

export const SOURCES = { weather: "https://api.weather.gov", soil: "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest", roadwork: "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed", route: "https://routes.googleapis.com/directions/v2:computeRoutes", aef: "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL" } as const;
export type Context = { io: Transport; now: Date; userAgent?: string; googleKey?: string; lvrEnabled?: boolean };
export const DEFAULT_NWS_USER_AGENT = "GridBridge (https://github.com/fradicus/Shellhacks-2026/issues)";
export const context = (): Context => ({ io: transport(), now: new Date(), userAgent: process.env.NWS_USER_AGENT?.trim() || DEFAULT_NWS_USER_AGENT, googleKey: process.env.GOOGLE_ROUTES_API_KEY, lvrEnabled: process.env.GOOGLE_LVR_ENABLED === "true" });
export function empty<T>(provider: keyof typeof SOURCES, request: unknown, reason: string, status: Envelope<T>["status"] = "unavailable", now = new Date()): Envelope<T> {
  return { schema_version: SCHEMA_VERSION, provider, status, request_hash: digest(request), retrieved_at: now.toISOString(), source_updated_at: null, valid_from: null, valid_to: null, source_url: SOURCES[provider], source_version: null, evidence_hash: null, coverage: { requested: 1, completed: 0, failed: 1, truncated: false }, data: null, limitations: [reason] };
}
const date = z.string().datetime({ offset: true });
const quantity = z.object({ value: z.number().finite().nullable() });
function fresh(value: string, now: Date, maxAge: number) { const age = now.getTime() - Date.parse(value); if (age < -300000) throw new Error("Provider timestamp is in the future"); return age <= maxAge; }
const fail = (error: unknown) => error instanceof Error ? error.message.slice(0, 200) : "Provider unavailable";
const cleanFailure = (provider: keyof typeof SOURCES, error: unknown) => `${provider}: ${fail(error).replace(/https?:\/\/\S+/g, "[provider URL]")}`;

const PointMetadata = z.object({ properties: z.object({ forecastHourly: z.string().url(), gridId: z.string(), gridX: z.number().int(), gridY: z.number().int() }) });
const Forecast = z.object({ properties: z.object({ generatedAt: date, updateTime: date, validTimes: z.string(), periods: z.array(z.object({ startTime: date, endTime: date, temperature: z.number().finite().nullable(), temperatureUnit: z.string().nullable(), windSpeed: z.string().nullable(), windDirection: z.string().nullable(), probabilityOfPrecipitation: quantity, shortForecast: z.string() })).max(200) }) });
const Alerts = z.object({ type: z.literal("FeatureCollection"), features: z.array(z.object({ id: z.string(), geometry: z.unknown().nullable(), properties: z.object({ event: z.string(), severity: z.string().nullable(), certainty: z.string().nullable(), urgency: z.string().nullable(), sent: date, onset: date.nullable(), expires: date, description: z.string(), affectedZones: z.array(z.string().url()).max(1000) }) })).max(2000), pagination: z.object({ next: z.string().optional() }).optional() });

export async function weather(point: Point, ctx: Context): Promise<Envelope<WeatherData>> {
  const result = empty<WeatherData>("weather", point, "Forecast and alerts apply to the queried point; no corridor all-clear.", "available", ctx.now);
  if (!ctx.userAgent) return { ...result, status: "not_configured", limitations: ["NWS_USER_AGENT identifying contact is required."] };
  try {
    PointSchema.parse(point);
    const headers = { "User-Agent": ctx.userAgent, Accept: "application/geo+json" };
    const metadata = await ctx.io(`${SOURCES.weather}/points/${point.lat},${point.lon}`, { headers });
    const info = PointMetadata.parse(metadata.value).properties;
    // Do not follow arbitrary URLs from even an approved response.
    const expected = `${SOURCES.weather}/gridpoints/${encodeURIComponent(info.gridId)}/${info.gridX},${info.gridY}/forecast/hourly`;
    if (info.forecastHourly !== expected) throw new Error("Unexpected forecast resource binding");
    const [forecastResponse, alertsResponse] = await Promise.all([ctx.io(expected, { headers }), ctx.io(`${SOURCES.weather}/alerts/active?point=${point.lat},${point.lon}`, { headers })]);
    const forecast = Forecast.parse(forecastResponse.value).properties;
    const alerts = Alerts.parse(alertsResponse.value);
    const isFresh = fresh(forecast.updateTime, ctx.now, 6 * 3600_000) && fresh(forecast.generatedAt, ctx.now, 6 * 3600_000);
    for (const alert of alerts.features) fresh(alert.properties.sent, ctx.now, Infinity);
    if (forecast.periods.some((p, i) => Date.parse(p.endTime) <= Date.parse(p.startTime) || (i > 0 && Date.parse(p.startTime) < Date.parse(forecast.periods[i - 1].endTime)))) throw new Error("Malformed forecast intervals");
    const periods = forecast.periods.filter((p) => Date.parse(p.endTime) > ctx.now.getTime());
    const active = alerts.features.filter((a) => Date.parse(a.properties.expires) > ctx.now.getTime());
    result.data = { scope: "point forecasts and NWS county/zone point alerts; null alert polygons remain included", samples: [{ point, updated_at: forecast.updateTime, alerts_checked_at: alertsResponse.retrieved, alert_coverage: "point_county_and_zone", forecast: periods.map((p) => ({ start: p.startTime, end: p.endTime, temperature: p.temperature, temperature_unit: p.temperatureUnit, wind_speed: p.windSpeed, wind_direction: p.windDirection, precipitation_probability: p.probabilityOfPrecipitation.value, description: p.shortForecast })), alerts: active.map((a) => ({ id: a.id, event: a.properties.event, severity: a.properties.severity, certainty: a.properties.certainty, urgency: a.properties.urgency, onset: a.properties.onset, expires: a.properties.expires, description: a.properties.description, geometry_available: a.geometry != null, affected_zones: a.properties.affectedZones })) }] };
    result.status = !isFresh || !periods.length ? "stale" : alerts.pagination?.next ? "partial" : "available";
    result.source_updated_at = forecast.updateTime; result.valid_from = periods[0]?.startTime ?? null; result.valid_to = periods.at(-1)?.endTime ?? null;
    result.coverage = { requested: 1, completed: 1, failed: 0, truncated: !!alerts.pagination?.next };
    result.evidence_hash = digest([metadata.hash, forecastResponse.hash, alertsResponse.hash]);
    result.retrieved_at = alertsResponse.retrieved;
    if (alerts.pagination?.next) result.limitations.push("Alert results are paginated; coverage is incomplete.");
    return result;
  } catch (error) { return empty("weather", point, cleanFailure("weather", error), "unavailable", ctx.now); }
}

const SoilResponse = z.object({ Table: z.array(z.array(z.union([z.string(), z.number(), z.null()]))).max(1003) });
const SOIL_COLUMNS = ["mukey", "muname", "areasymbol", "saverest", "cokey", "compname", "comppct_r", "drainagecl", "hydgrp", "chkey", "hzdept_r", "hzdepb_r", "ph1to1h2o_r"] as const;
function finiteOrNull(value: string | number | null, label: string): number | null {
  if (value == null) return null;
  const n = Number(value);
  if (!Number.isFinite(n)) throw new Error(`Invalid ${label}`);
  return n;
}
export async function soil(point: Point, ctx: Context): Promise<Envelope<SoilData>> {
  const result = empty<SoilData>("soil", point, "SSURGO map-unit context, not a site test or engineering approval.", "available", ctx.now);
  try {
    PointSchema.parse(point);
    // Point has already passed strict finite/range validation; no user SQL or identifiers.
    // Horizon pH is SSURGO ph1to1h2o_r with hzdept_r/hzdepb_r in centimeters (C15 depth+units rule).
    const query = `SELECT TOP 1001 m.mukey,m.muname,l.areasymbol,s.saverest,c.cokey,c.compname,c.comppct_r,c.drainagecl,c.hydgrp,ch.chkey,ch.hzdept_r,ch.hzdepb_r,ch.ph1to1h2o_r FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT(${point.lon} ${point.lat})') p JOIN mapunit m ON m.mukey=p.mukey JOIN legend l ON l.lkey=m.lkey JOIN sacatalog s ON s.areasymbol=l.areasymbol LEFT JOIN component c ON c.mukey=m.mukey LEFT JOIN chorizon ch ON ch.cokey=c.cokey ORDER BY m.mukey,c.cokey,ch.hzdept_r,ch.chkey`;
    const response = await ctx.io(SOURCES.soil, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, format: "JSON+COLUMNNAME+METADATA" }) });
    const rows = SoilResponse.parse(response.value).Table;
    if (JSON.stringify(rows[0]) !== JSON.stringify([...SOIL_COLUMNS]) || !rows[1] || rows[1].length !== SOIL_COLUMNS.length) throw new Error("Unexpected SDA table metadata");
    const map = new Map<string, SoilData["map_units"][number]>();
    type MutableComponent = SoilData["map_units"][number]["components"][number] & { horizons: NonNullable<SoilData["map_units"][number]["components"][number]["horizons"]> };
    const components = new Map<string, MutableComponent>();
    for (const row of rows.slice(2, 1002)) {
      if (row.length !== SOIL_COLUMNS.length || !row[0] || !row[1] || !row[2]) throw new Error("Malformed soil row");
      const [key, name, area, vintage, component, componentName, percent, drainage, hydro, chkey, depthTop, depthBottom, ph] = row;
      const id = String(key); const sourceDate = vintage == null ? null : String(vintage);
      if (!map.has(id)) map.set(id, { mukey: id, name: String(name), area_symbol: String(area), survey_updated_at: sourceDate, components: [] });
      if (component == null) continue;
      const componentId = `${id}:${component}`;
      let entry = components.get(componentId);
      if (!entry) {
        const percentage = percent == null ? null : Number(percent);
        if (percentage != null && (!Number.isFinite(percentage) || percentage < 0 || percentage > 100)) throw new Error("Invalid component percentage");
        entry = { cokey: String(component), name: componentName == null ? null : String(componentName), percent: percentage, drainage_class: drainage == null ? null : String(drainage), hydrologic_group: hydro == null ? null : String(hydro), horizons: [] };
        components.set(componentId, entry);
        map.get(id)!.components.push(entry);
      }
      if (chkey == null) continue;
      const top = finiteOrNull(depthTop, "horizon top depth");
      const bottom = finiteOrNull(depthBottom, "horizon bottom depth");
      if (top != null && bottom != null && bottom < top) throw new Error("Reversed horizon depths");
      const phValue = finiteOrNull(ph, "horizon pH");
      if (phValue != null && (phValue < 0 || phValue > 14)) throw new Error("pH out of range");
      if (entry.horizons.some((horizon) => horizon.chkey === String(chkey))) continue;
      entry.horizons.push({ chkey: String(chkey), depth_top_cm: top, depth_bottom_cm: bottom, ph_h2o_1_to_1: phValue, ph_method: "1:1 soil-water", depth_unit: "cm" });
    }
    result.data = { map_units: [...map.values()], scope: "mapped soil components and horizon survey pH at point; reference survey with depth in cm, not a live soil test" };
    result.status = map.size ? rows.length > 1002 ? "partial" : "available" : "out_of_coverage";
    result.coverage = { requested: 1, completed: map.size ? 1 : 0, failed: map.size ? 0 : 1, truncated: rows.length > 1002 }; result.evidence_hash = response.hash; result.retrieved_at = response.retrieved;
    if (map.size && ![...components.values()].some((c) => c.horizons.some((h) => h.ph_h2o_1_to_1 != null))) {
      result.limitations.push("No SSURGO 1:1 soil-water pH values were published for the returned horizons; depths remain reported when present.");
    }
    return result;
  } catch (error) { return empty("soil", point, cleanFailure("soil", error), "unavailable", ctx.now); }
}

const Workzones = z.object({ type: z.literal("FeatureCollection"), feed_info: z.object({ publisher: z.string(), version: z.literal("4.2"), update_date: date }).optional(), road_event_feed_info: z.object({ publisher: z.string(), version: z.literal("4.2"), update_date: date }).optional(), features: z.array(z.object({ id: z.union([z.string(), z.number()]).optional(), geometry: z.object({ type: z.enum(["LineString", "MultiLineString"]), coordinates: z.unknown() }), properties: z.object({ core_details: z.object({ road_names: z.array(z.string()), direction: z.string(), description: z.string().optional(), update_date: date.optional() }), start_date: date, end_date: date, vehicle_impact: z.string(), event_status: z.string().optional(), is_start_date_verified: z.boolean().optional(), is_end_date_verified: z.boolean().optional(), restrictions: z.array(z.object({ type: z.string(), value: z.number().finite().optional(), unit: z.string().optional() })).max(100).optional() }) })).max(20000) });
export function inWashington(point: Point) { return point.lat >= 45.5 && point.lat <= 49.01 && point.lon >= -124.9 && point.lon <= -116.8; }
export async function roadwork(point: Point, ctx: Context): Promise<Envelope<RoadworkData>> {
  if (!inWashington(point)) return empty("roadwork", point, "Only the WSDOT feed is supported; other jurisdictions are unavailable.", "out_of_coverage", ctx.now);
  const contained = await washingtonContains(point);
  if (contained !== true) return empty("roadwork", point, contained === null ? "Washington boundary verification unavailable." : "Point is outside the verified Washington boundary.", contained === null ? "unavailable" : "out_of_coverage", ctx.now);
  const result = empty<RoadworkData>("roadwork", point, "WSDOT reported work zones only; bounding-box vicinity is not proof of a road connection or complete closures.", "available", ctx.now);
  try {
    const response = await ctx.io(SOURCES.roadwork, {}, 8_000_000); const feed = Workzones.parse(response.value); const meta = feed.feed_info ?? feed.road_event_feed_info;
    if (!meta || !/washington|wsdot/i.test(meta.publisher)) throw new Error("Unexpected WSDOT publisher");
    const current = fresh(meta.update_date, ctx.now, 15 * 60_000);
    let malformed = false;
    const events = feed.features.filter((f) => {
      if (Date.parse(f.properties.end_date) < Date.parse(f.properties.start_date)) throw new Error("Reversed work-zone dates");
      if (f.properties.core_details.update_date) fresh(f.properties.core_details.update_date, ctx.now, Infinity);
      const line = z.array(z.tuple([z.number().finite().min(-180).max(180), z.number().finite().min(-90).max(90)]));
      const parsed = (f.geometry.type === "LineString" ? line : z.array(line)).safeParse(f.geometry.coordinates);
      if (!parsed.success) { malformed = true; return false; }
      const coords = (f.geometry.type === "LineString" ? [parsed.data] : parsed.data) as number[][][];
      const points = coords.flat();
      // Inclusive bbox intersection catches long segments whose vertices lie outside the vicinity.
      const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
      return Date.parse(f.properties.end_date) > ctx.now.getTime() && Math.min(...xs) <= point.lon + .05 && Math.max(...xs) >= point.lon - .05 && Math.min(...ys) <= point.lat + .05 && Math.max(...ys) >= point.lat - .05;
    }).slice(0, 100);
    result.data = { jurisdictions: ["WA: WSDOT reported network (not complete state coverage)"], scope: "0.05-degree point vicinity; includes future reported work zones", events: events.map((f) => ({ id: String(f.id ?? digest(f)), road_names: f.properties.core_details.road_names, direction: f.properties.core_details.direction, start: f.properties.start_date, end: f.properties.end_date, vehicle_impact: f.properties.vehicle_impact, description: f.properties.core_details.description ?? null, event_status: f.properties.event_status ?? null, start_verified: f.properties.is_start_date_verified ?? null, end_verified: f.properties.is_end_date_verified ?? null, source_updated_at: f.properties.core_details.update_date ?? null, restrictions: (f.properties.restrictions ?? []).map((r) => ({ type: r.type, value: r.value ?? null, unit: r.unit ?? null })) })) };
    result.status = !current ? "stale" : malformed || events.length === 100 ? "partial" : "available";
    result.source_updated_at = meta.update_date; result.source_version = meta.version; result.evidence_hash = response.hash; result.retrieved_at = response.retrieved;
    result.coverage = { requested: 1, completed: 1, failed: malformed ? 1 : 0, truncated: events.length === 100 };
    if (malformed) result.limitations.push("Some feed geometries could not be assessed.");
    return result;
  } catch (error) { return empty("roadwork", point, cleanFailure("roadwork", error), "unavailable", ctx.now); }
}

const GoogleResponse = z.object({ routes: z.array(z.object({ distanceMeters: z.number().finite().nonnegative(), duration: z.string().regex(/^\d+(\.\d+)?s$/), polyline: z.object({ encodedPolyline: z.string().max(200000) }), travelAdvisory: z.object({ routeRestrictionsPartiallyIgnored: z.boolean().optional() }).optional(), warnings: z.array(z.string()).max(100).optional() })).min(1).max(3) });
export async function truckRoute(request: RouteRequest, ctx: Context): Promise<{ result: Envelope<RouteData>; polyline: string | null }> {
  if ([request.origin, request.destination].some((p) => p.lat < 24 || p.lat > 49.5 || p.lon < -125 || p.lon > -66)) return { result: empty("route", request, "This adapter is restricted to contiguous-US routing; Alaska, Hawaii, territories and other countries are unsupported.", "out_of_coverage", ctx.now), polyline: null };
  if (!ctx.googleKey || !ctx.lvrEnabled) return { result: empty("route", request, "Google Routes key and separately provisioned LVR access are required.", "not_configured", ctx.now), polyline: null };
  try {
    RouteRequestSchema.parse(request);
    const { truck } = request; const convert = millimeters;
    const response = await ctx.io(SOURCES.route, { method: "POST", headers: { "Content-Type": "application/json", "X-Goog-Api-Key": ctx.googleKey, "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.travelAdvisory.routeRestrictionsPartiallyIgnored,routes.warnings" }, body: JSON.stringify({ origin: { location: { latLng: { latitude: request.origin.lat, longitude: request.origin.lon } } }, destination: { location: { latLng: { latitude: request.destination.lat, longitude: request.destination.lon } } }, departureTime: request.departure_at, travelMode: "TRUCK", routingPreference: "TRAFFIC_AWARE_OPTIMAL", routeModifiers: { vehicleInfo: { totalHeightMm: convert(truck.height_m), totalWidthMm: convert(truck.width_m), totalLengthMm: convert(truck.length_m), totalWeightKg: Math.floor(truck.gross_weight_kg), totalAxleCount: truck.axle_count, ...(truck.trailers.length ? { trailerInfo: truck.trailers.map((t) => ({ lengthMm: convert(t.length_m) })) } : {}), hazardousGoodsTypes: truck.hazmat } } }) });
    const route = GoogleResponse.parse(response.value).routes[0]; const seconds = Number(route.duration.slice(0, -1));
    if (!Number.isFinite(seconds) || seconds > 30 * 86400) throw new Error("Invalid route duration");
    const result = empty<RouteData>("route", request, "Google Maps route is not guaranteed safe or legal. Check road authority restrictions and actual vehicle clearance.", "available", ctx.now);
    result.evidence_hash = response.hash; result.retrieved_at = response.retrieved;
    result.data = { distance_m: route.distanceMeters, travel_seconds: seconds, eta: new Date(Date.parse(request.departure_at) + seconds * 1000).toISOString(), restrictions_partially_ignored: route.travelAdvisory?.routeRestrictionsPartiallyIgnored ?? false, warnings: route.warnings ?? [], attribution: "Google Maps" };
    result.coverage = { requested: 1, completed: 1, failed: 0, truncated: false };
    result.valid_from = request.departure_at; result.valid_to = result.data.eta;
    if (result.data.restrictions_partially_ignored) { result.status = "partial"; result.limitations.push("Google returned a best-effort route that ignores vehicle restrictions."); }
    if (result.data.warnings.length) { result.status = "partial"; result.limitations.push("Google route warnings require review."); }
    // Ephemeral internal geometry only: never returned, logged or persisted as public route data.
    return { result, polyline: route.polyline.encodedPolyline };
  } catch { return { result: empty("route", request, "Google truck route unavailable or invalid; no passenger-car fallback.", "unavailable", ctx.now), polyline: null }; }
}
