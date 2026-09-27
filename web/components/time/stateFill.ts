// State fills under the time layer: a map's colors (neighbors differ) or drawn projects per state.
type Ring = [number, number][];
export interface StateFeature {
  properties: { GEOID: string; STUSAB: string };
  geometry: { type: "Polygon"; coordinates: Ring[] } | { type: "MultiPolygon"; coordinates: Ring[][] };
}

/** Muted and cool, so the warm project points stay the brightest thing on the map. */
export const MAP_PALETTE = ["#5d8fd6", "#3fa69a", "#9178c9", "#c0658e", "#6fa35f", "#4fa3c7"];

/**
 * A color index per state (GEOID) with no two neighbors alike. Neighbors are states sharing a border vertex:
 * the Census generalized file is topologically consistent, so shared borders are the same coordinates.
 * Greedy, most-connected first, least-used color among the free ones so the colors spread evenly.
 */
export function neighborColors(features: StateFeature[], k = MAP_PALETTE.length): Map<string, number> {
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
