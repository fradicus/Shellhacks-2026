import "server-only";
import { z } from "zod";

// Typed locations only. US Census Geocoder (exact street addresses) first, then OpenStreetMap Nominatim (places).
// Both are free and keyless; results are cached and Nominatim is held to one request per second per its usage policy.
const CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress";
const NOMINATIM = "https://nominatim.openstreetmap.org/search";
const USER_AGENT = "GridBridge (https://github.com/fradicus/Shellhacks-2026/issues)";

export type GeocodeResult = { label: string; lat: number; lon: number; source: "US Census Geocoder" | "OpenStreetMap Nominatim"; attribution: string };

const Census = z.object({ result: z.object({ addressMatches: z.array(z.object({ matchedAddress: z.string(), coordinates: z.object({ x: z.number(), y: z.number() }) })) }) });
const Nominatim = z.array(z.object({ lat: z.string(), lon: z.string(), display_name: z.string() })).max(5);

const cache = new Map<string, GeocodeResult | null>();
let lastNominatim = 0;

async function json(url: string): Promise<unknown> {
  const response = await fetch(url, { headers: { "User-Agent": USER_AGENT, Accept: "application/json" }, signal: AbortSignal.timeout(10_000), cache: "no-store" });
  if (!response.ok) throw new Error(`Geocoder HTTP ${response.status}`);
  return response.json();
}

export function cleanQuery(q: string | null): string | null {
  const text = (q ?? "").replace(/\s+/g, " ").trim();
  return text.length >= 3 && text.length <= 200 ? text : null;
}

export async function geocode(query: string): Promise<GeocodeResult | null> {
  const key = query.toLowerCase();
  if (cache.has(key)) return cache.get(key)!;
  let found: GeocodeResult | null = null;
  try {
    const c = Census.parse(await json(`${CENSUS}?${new URLSearchParams({ address: query, benchmark: "Public_AR_Current", format: "json" })}`)).result.addressMatches[0];
    if (c) found = { label: c.matchedAddress, lat: c.coordinates.y, lon: c.coordinates.x, source: "US Census Geocoder", attribution: "U.S. Census Bureau" };
  } catch { /* fall through to Nominatim */ }
  if (!found) {
    const wait = lastNominatim + 1100 - Date.now();
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    lastNominatim = Date.now();
    const n = Nominatim.parse(await json(`${NOMINATIM}?${new URLSearchParams({ q: query, format: "jsonv2", limit: "1", countrycodes: "us" })}`))[0];
    if (n) found = { label: n.display_name, lat: Number(n.lat), lon: Number(n.lon), source: "OpenStreetMap Nominatim", attribution: "© OpenStreetMap contributors (ODbL)" };
  }
  if (found && (!Number.isFinite(found.lat) || !Number.isFinite(found.lon))) found = null;
  if (cache.size > 500) cache.clear();
  cache.set(key, found);
  return found;
}
