import "server-only";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { gunzipSync } from "node:zlib";
import { z } from "zod";

// Committed by pipeline/weather_history (NOAA NCEI GHCN-Daily, 2016–2025). Read-only here; never fetched at request time.
const DATA_DIR = resolve(process.cwd(), "..", "data", "weather_history");
/** Same caps the pipeline used to assign project centers; a clicked point beyond them gets no station, not a far one. */
export const RAIN_MAX_MI = 30;
export const WIND_MAX_MI = 60;

const num = z.number().finite().nullable();
const Station = z.object({ name: z.string(), lat: z.number(), lon: z.number(), platforms: z.array(z.string()), completeness: z.record(z.string(), z.number()), file: z.string().regex(/^stations\/[A-Z0-9]+\.json(\.gz)?$/) });
const Index = z.object({
  site_coverage: z.object({ sites: z.number(), covered: z.number() }).passthrough().optional(),
  rule_version: z.string(), window: z.object({ start: z.string(), end: z.string() }), generated_at: z.string(),
  source: z.object({ dataset: z.string(), citation: z.string().url() }).passthrough(),
  stations: z.record(z.string(), Station),
});
const Series = z.object({
  station: z.object({ id: z.string(), name: z.string(), lat: z.number(), lon: z.number() }).passthrough(),
  start: z.string(), end: z.string(), prcp_in: z.array(num), tmax_f: z.array(num), wsf2_mph: z.array(num),
  tmin_f: z.array(num).optional(), snow_in: z.array(num).optional(),
  source: z.object({ url: z.string().url(), sha256: z.string(), retrieved_at: z.string() }).passthrough(),
});

export type StationRef = { id: string; name: string; lat: number; lon: number; distance_mi: number; source_url: string; retrieved_at: string };
export type WeatherHistory = {
  /** "committed" = pipeline/weather_history files; "live" = the same NOAA selection rules run on request for a new point. */
  origin: "committed" | "live";
  window: { start: string; end: string };
  rule_version: string;
  citation: string;
  rain: StationRef;
  wind: StationRef | null;
  /** Day-aligned from window.start. Rain and heat come from `rain`; wind from `wind` (often an airport). Missing stays null. */
  prcp_in: (number | null)[];
  tmax_f: (number | null)[];
  /** Freeze and snow from the rain/heat station; null when this record predates them or the station never reports them. */
  tmin_f: (number | null)[] | null;
  snow_in: (number | null)[] | null;
  wsf2_mph: (number | null)[] | null;
};

const miles = (a: { lat: number; lon: number }, b: { lat: number; lon: number }) => {
  const r = Math.PI / 180;
  const h = Math.sin((b.lat - a.lat) * r / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin((b.lon - a.lon) * r / 2) ** 2;
  return 3958.8 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
};

let indexCache: z.infer<typeof Index> | null = null;
async function index() {
  indexCache ??= Index.parse(JSON.parse(await readFile(resolve(DATA_DIR, "index.json"), "utf8")));
  return indexCache;
}
const seriesCache = new Map<string, z.infer<typeof Series>>();
async function series(file: string) {
  if (!seriesCache.has(file)) {
    const bytes = await readFile(resolve(DATA_DIR, file));
    seriesCache.set(file, Series.parse(JSON.parse((file.endsWith(".gz") ? gunzipSync(bytes) : bytes).toString("utf8"))));
  }
  return seriesCache.get(file)!;
}

/** Committed stations first; anywhere else, the same NOAA rules live. Null when no complete station is within the caps. */
export async function historyAt(point: { lat: number; lon: number }): Promise<WeatherHistory | null> {
  return (await committedAt(point)) ?? (await liveAt(point));
}

async function committedAt(point: { lat: number; lon: number }): Promise<WeatherHistory | null> {
  const idx = await index();
  const ranked = Object.entries(idx.stations).map(([id, s]) => ({ id, s, d: miles(point, s) })).sort((a, b) => a.d - b.d || a.id.localeCompare(b.id));
  const rain = ranked.find((x) => x.d <= RAIN_MAX_MI && (x.s.completeness.prcp_in ?? 0) >= 0.95 && (x.s.completeness.tmax_f ?? 0) >= 0.95);
  if (!rain) return null;
  const wind = ranked.find((x) => x.d <= WIND_MAX_MI && (x.s.completeness.wsf2_mph ?? 0) >= 0.95);
  const r = await series(rain.s.file);
  const w = wind ? (wind.id === rain.id ? r : await series(wind.s.file)) : null;
  const ref = (x: { id: string; s: z.infer<typeof Station>; d: number }, data: z.infer<typeof Series>): StationRef =>
    ({ id: x.id, name: x.s.name, lat: x.s.lat, lon: x.s.lon, distance_mi: Math.round(x.d * 10) / 10, source_url: data.source.url, retrieved_at: data.source.retrieved_at });
  return {
    origin: "committed", window: idx.window, rule_version: idx.rule_version, citation: idx.source.citation,
    rain: ref(rain, r), wind: wind && w ? ref(wind, w) : null,
    prcp_in: r.prcp_in, tmax_f: r.tmax_f, tmin_f: r.tmin_f ?? null, snow_in: r.snow_in ?? null, wsf2_mph: w ? w.wsf2_mph : null,
  };
}

// ---- Live lookup: a TypeScript port of pipeline/weather_history/core.py for points away from the committed stations ----
const NCEI_SEARCH = "https://www.ncei.noaa.gov/access/services/search/v1/data";
const NCEI_DATA = "https://www.ncei.noaa.gov/access/services/data/v1";
const CITATION = "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily";
const MAX_DOWNLOADS = 4; // bounded work per request: nearest candidates only

async function ncei(url: string): Promise<unknown> {
  const response = await fetch(url, { signal: AbortSignal.timeout(20_000), headers: { "User-Agent": "GridBridge (https://github.com/fradicus/Shellhacks-2026/issues)" }, cache: "no-store" });
  if (!response.ok) throw new Error(`NCEI HTTP ${response.status}`);
  return response.json();
}

const SearchResults = z.object({ results: z.array(z.object({
  location: z.object({ coordinates: z.tuple([z.number(), z.number()]) }),
  stations: z.array(z.object({ id: z.string(), name: z.string().optional(), dataTypes: z.array(z.object({ id: z.string(), startDate: z.string().optional(), endDate: z.string().optional() }).passthrough()) }).passthrough()).min(1),
}).passthrough()).max(2000) });
const Rows = z.array(z.object({ DATE: z.string(), PRCP: z.string().optional(), TMAX: z.string().optional(), TMIN: z.string().optional(), SNOW: z.string().optional(), WSF2: z.string().optional() }).passthrough()).max(5000);

type Candidate = { id: string; name: string; lat: number; lon: number; hasWind: boolean; d: number };
type Downloaded = { url: string; retrieved_at: string; prcp_in: (number | null)[]; tmax_f: (number | null)[]; tmin_f: (number | null)[]; snow_in: (number | null)[]; wsf2_mph: (number | null)[] };
const liveCache = new Map<string, Downloaded | null>(); // station id -> series (null = failed or incomplete)

const WINDOW = { start: "2016-01-01", end: "2025-12-31" };
function windowDays(): string[] {
  const out: string[] = [];
  for (let t = Date.parse(`${WINDOW.start}T00:00:00Z`); t <= Date.parse(`${WINDOW.end}T00:00:00Z`); t += 86_400_000) out.push(new Date(t).toISOString().slice(0, 10));
  return out;
}
const value = (v: string | undefined, digits: number) => {
  if (v === undefined || v.trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? Math.round(n * 10 ** digits) / 10 ** digits : null;
};
const complete = (v: (number | null)[]) => v.filter((x) => x !== null).length / v.length;

async function download(id: string): Promise<Downloaded | null> {
  if (liveCache.has(id)) return liveCache.get(id)!;
  const url = `${NCEI_DATA}?${new URLSearchParams({ dataset: "daily-summaries", stations: id, startDate: WINDOW.start, endDate: WINDOW.end, dataTypes: "PRCP,TMAX,TMIN,SNOW,WSF2", units: "standard", format: "json" })}`;
  let out: Downloaded | null = null;
  try {
    const rows = new Map(Rows.parse(await ncei(url)).map((r) => [r.DATE, r]));
    const days = windowDays();
    out = { url, retrieved_at: new Date().toISOString(), prcp_in: days.map((d) => value(rows.get(d)?.PRCP, 2)), tmax_f: days.map((d) => value(rows.get(d)?.TMAX, 0)), tmin_f: days.map((d) => value(rows.get(d)?.TMIN, 0)), snow_in: days.map((d) => value(rows.get(d)?.SNOW, 1)), wsf2_mph: days.map((d) => value(rows.get(d)?.WSF2, 1)) };
  } catch { out = null; }
  liveCache.set(id, out);
  return out;
}

async function liveAt(point: { lat: number; lon: number }): Promise<WeatherHistory | null> {
  const pad = 0.9; // degrees, a little beyond WIND_MAX_MI so airports are found
  const bbox = [point.lat + pad, point.lon - pad, point.lat - pad, point.lon + pad].map((n) => n.toFixed(3)).join(",");
  const search = SearchResults.parse(await ncei(`${NCEI_SEARCH}?${new URLSearchParams({ dataset: "daily-summaries", bbox, startDate: `${WINDOW.start}T00:00:00`, endDate: `${WINDOW.end}T23:59:59`, dataTypes: "TMAX", limit: "1000" })}`));
  const spans = (types: { id: string; startDate?: string; endDate?: string }[], id: string) => types.some((t) => t.id === id && (t.startDate ?? "9") <= WINDOW.start && (t.endDate ?? "") >= WINDOW.end);
  const candidates: Candidate[] = search.results.flatMap((r) => {
    const st = r.stations[0], [lon, lat] = r.location.coordinates;
    if (!spans(st.dataTypes, "PRCP") || !spans(st.dataTypes, "TMAX")) return [];
    return [{ id: st.id, name: st.name ?? st.id, lat, lon, hasWind: spans(st.dataTypes, "WSF2"), d: miles(point, { lat, lon }) }];
  }).sort((a, b) => a.d - b.d || a.id.localeCompare(b.id));

  let rain: { c: Candidate; s: Downloaded } | null = null;
  for (const c of candidates.filter((x) => x.d <= RAIN_MAX_MI).slice(0, MAX_DOWNLOADS)) {
    const s = await download(c.id);
    if (s && complete(s.prcp_in) >= 0.95 && complete(s.tmax_f) >= 0.95) { rain = { c, s }; break; }
  }
  if (!rain) return null;
  let wind: { c: Candidate; s: Downloaded } | null = null;
  for (const c of candidates.filter((x) => x.d <= WIND_MAX_MI && x.hasWind).slice(0, MAX_DOWNLOADS)) {
    const s = await download(c.id);
    if (s && complete(s.wsf2_mph) >= 0.95) { wind = { c, s }; break; }
  }
  const ref = (x: { c: Candidate; s: Downloaded }): StationRef => ({ id: x.c.id, name: x.c.name, lat: x.c.lat, lon: x.c.lon, distance_mi: Math.round(x.c.d * 10) / 10, source_url: x.s.url, retrieved_at: x.s.retrieved_at });
  return {
    origin: "live", window: WINDOW, rule_version: "weather-history-v1", citation: CITATION,
    rain: ref(rain), wind: wind ? ref(wind) : null, prcp_in: rain.s.prcp_in, tmax_f: rain.s.tmax_f, tmin_f: rain.s.tmin_f, snow_in: rain.s.snow_in, wsf2_mph: wind ? wind.s.wsf2_mph : null,
  };
}

// ---- Recent observations: the latest ~13 months from NOAA for "this time last year" (the 10-year record ends 2025-12-31) ----
export type RecentSeries = { start: string; end: string; source_url: string; retrieved_at: string; prcp_in: (number | null)[]; tmax_f: (number | null)[]; tmin_f: (number | null)[]; snow_in: (number | null)[]; wsf2_mph: (number | null)[] | null };
const recentCache = new Map<string, { at: number; value: RecentSeries }>();
export const STATION_ID = /^[A-Z]{2}[A-Z0-9]{9}$/;

export async function recentAt(rainId: string, windId: string | null, now = new Date()): Promise<RecentSeries> {
  const key = `${rainId}|${windId ?? ""}`;
  const hit = recentCache.get(key);
  if (hit && now.getTime() - hit.at < 6 * 3600_000) return hit.value;
  const end = new Date(now.getTime() - 86_400_000).toISOString().slice(0, 10); // NOAA posts with a lag; missing tail days stay null
  const start = new Date(now.getTime() - 400 * 86_400_000).toISOString().slice(0, 10);
  const url = (id: string, types: string) => `${NCEI_DATA}?${new URLSearchParams({ dataset: "daily-summaries", stations: id, startDate: start, endDate: end, dataTypes: types, units: "standard", format: "json" })}`;
  const rainUrl = url(rainId, "PRCP,TMAX,TMIN,SNOW");
  const [rainRows, windRows] = await Promise.all([ncei(rainUrl).then((v) => Rows.parse(v)), windId ? ncei(url(windId, "WSF2")).then((v) => Rows.parse(v)).catch(() => null) : Promise.resolve(null)]);
  const days: string[] = [];
  for (let t = Date.parse(`${start}T00:00:00Z`); t <= Date.parse(`${end}T00:00:00Z`); t += 86_400_000) days.push(new Date(t).toISOString().slice(0, 10));
  const r = new Map(rainRows.map((row) => [row.DATE, row])), w = windRows ? new Map(windRows.map((row) => [row.DATE, row])) : null;
  const result: RecentSeries = {
    start, end, source_url: rainUrl, retrieved_at: new Date().toISOString(),
    prcp_in: days.map((d) => value(r.get(d)?.PRCP, 2)), tmax_f: days.map((d) => value(r.get(d)?.TMAX, 0)), tmin_f: days.map((d) => value(r.get(d)?.TMIN, 0)),
    snow_in: days.map((d) => value(r.get(d)?.SNOW, 1)), wsf2_mph: w ? days.map((d) => value(w.get(d)?.WSF2, 1)) : null,
  };
  recentCache.set(key, { at: now.getTime(), value: result });
  return result;
}

export type StationSummary = { id: string; name: string; lat: number; lon: number; wind: boolean; snow: boolean; freeze: boolean };
/** Every committed station, for the map's coverage layer. Flags say which daily records are at least 95% complete. */
export async function committedStations(): Promise<{ stations: StationSummary[]; window: { start: string; end: string }; sites: number | null; covered: number | null }> {
  const idx = await index();
  const ok = (s: z.infer<typeof Station>, k: string) => (s.completeness[k] ?? 0) >= 0.95;
  return {
    window: idx.window, sites: idx.site_coverage?.sites ?? null, covered: idx.site_coverage?.covered ?? null,
    stations: Object.entries(idx.stations).map(([id, s]) => ({ id, name: s.name, lat: s.lat, lon: s.lon, wind: ok(s, "wsf2_mph"), snow: ok(s, "snow_in"), freeze: ok(s, "tmin_f") })),
  };
}
