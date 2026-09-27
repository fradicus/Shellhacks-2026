// Point inks: each state's projects are drawn in one pen color, and no two neighboring states share one.
type Ring = [number, number][];
export interface StateFeature {
  properties: { GEOID: string; STUSAB: string };
  geometry: { type: "Polygon"; coordinates: Ring[] } | { type: "MultiPolygon"; coordinates: Ring[][] };
}

/** Gel-pen inks, bright on the dark basemap. None is grey, which is the out-of-scope trace. */
export const INKS = ["#ff6b81", "#ffa94d", "#ffe066", "#51e0a0", "#4cc9f0", "#b197fc"];
/** A project with no stored state. */
export const NO_STATE_INK = "#c9d1e0";

/**
 * A color index per state (GEOID) with no two neighbors alike. Neighbors are states sharing a border vertex:
 * the Census generalized file is topologically consistent, so shared borders are the same coordinates.
 * Greedy, most-connected first, least-used color among the free ones so the colors spread evenly.
 */
export function neighborColors(features: StateFeature[], k = INKS.length): Map<string, number> {
  const owners = new Map<string, Set<string>>();
  for (const f of features) {
    const g = f.geometry;
    for (const ring of (g.type === "Polygon" ? [g.coordinates] : g.coordinates).flat())
      for (const [x, y] of ring) {
        const key = `${x},${y}`;
        owners.set(key, (owners.get(key) ?? new Set()).add(f.properties.GEOID));
      }
  }
  const adj = new Map(features.map((f) => [f.properties.GEOID, new Set<string>()]));
  for (const ids of owners.values()) for (const a of ids) for (const b of ids) if (a !== b) adj.get(a)!.add(b);
  const order = [...adj.keys()].sort((a, b) => adj.get(b)!.size - adj.get(a)!.size || a.localeCompare(b));
  const color = new Map<string, number>();
  const used = Array<number>(k).fill(0);
  for (const id of order) {
    const taken = new Set([...adj.get(id)!].map((n) => color.get(n)));
    let best = -1;
    for (let c = 0; c < k; c++) if (!taken.has(c) && (best < 0 || used[c] < used[best])) best = c;
    // ponytail: greedy can in theory run out of colors; the test proves 6 is enough for the committed file.
    color.set(id, Math.max(best, 0));
    used[Math.max(best, 0)]++;
  }
  return color;
}

/** State FIPS → ink, computed on the server so the boundary file never ships to the browser. */
export const stateInks = (features: StateFeature[]): Record<string, string> =>
  Object.fromEntries([...neighborColors(features)].map(([fips, c]) => [fips, INKS[c]]));
