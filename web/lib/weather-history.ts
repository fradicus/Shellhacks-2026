import "server-only";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { z } from "zod";

// Committed by pipeline/weather_history (NOAA NCEI GHCN-Daily, 2016–2025). Read-only here; never fetched at request time.
const DATA_DIR = resolve(process.cwd(), "..", "data", "weather_history");
/** Same caps the pipeline used to assign project centers; a clicked point beyond them gets no station, not a far one. */
export const RAIN_MAX_MI = 30;
export const WIND_MAX_MI = 60;

const num = z.number().finite().nullable();
const Station = z.object({ name: z.string(), lat: z.number(), lon: z.number(), platforms: z.array(z.string()), completeness: z.record(z.string(), z.number()), file: z.string().regex(/^stations\/[A-Z0-9]+\.json$/) });
const Index = z.object({
  rule_version: z.string(), window: z.object({ start: z.string(), end: z.string() }), generated_at: z.string(),
  source: z.object({ dataset: z.string(), citation: z.string().url() }).passthrough(),
  stations: z.record(z.string(), Station),
});
const Series = z.object({
  station: z.object({ id: z.string(), name: z.string(), lat: z.number(), lon: z.number() }).passthrough(),
  start: z.string(), end: z.string(), prcp_in: z.array(num), tmax_f: z.array(num), wsf2_mph: z.array(num),
  source: z.object({ url: z.string().url(), sha256: z.string(), retrieved_at: z.string() }).passthrough(),
});

export type StationRef = { id: string; name: string; lat: number; lon: number; distance_mi: number; source_url: string; retrieved_at: string };
export type WeatherHistory = {
  window: { start: string; end: string };
  rule_version: string;
  citation: string;
  rain: StationRef;
  wind: StationRef | null;
  /** Day-aligned from window.start. Rain and heat come from `rain`; wind from `wind` (often an airport). Missing stays null. */
  prcp_in: (number | null)[];
  tmax_f: (number | null)[];
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
  if (!seriesCache.has(file)) seriesCache.set(file, Series.parse(JSON.parse(await readFile(resolve(DATA_DIR, file), "utf8"))));
  return seriesCache.get(file)!;
}

/** Nearest committed station with complete rain/heat (and, separately, wind) records. Null when none is within the caps. */
export async function historyAt(point: { lat: number; lon: number }): Promise<WeatherHistory | null> {
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
    window: idx.window, rule_version: idx.rule_version, citation: idx.source.citation,
    rain: ref(rain, r), wind: wind && w ? ref(wind, w) : null,
    prcp_in: r.prcp_in, tmax_f: r.tmax_f, wsf2_mph: w ? w.wsf2_mph : null,
  };
}
