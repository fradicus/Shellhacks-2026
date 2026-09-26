import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { z } from "zod";
import type { Point } from "./contracts";

const ring = z.array(z.tuple([z.number().finite(), z.number().finite()])).min(4).max(100000);
const polygon = z.array(ring).min(1).max(10000);
const boundary = z.object({ type: z.literal("FeatureCollection"), features: z.array(z.object({ properties: z.object({ STATE: z.literal("53") }), geometry: z.discriminatedUnion("type", [z.object({ type: z.literal("Polygon"), coordinates: polygon }), z.object({ type: z.literal("MultiPolygon"), coordinates: z.array(polygon).max(10000) })]) })).length(1) });
function inside(point: Point, coordinates: number[][]): boolean | null {
  let contains = false;
  for (let i = 0, j = coordinates.length - 1; i < coordinates.length; j = i++) {
    const [x, y] = coordinates[i], [x2, y2] = coordinates[j];
    const cross = (point.lon - x) * (y2 - y) - (point.lat - y) * (x2 - x);
    if (Math.abs(cross) < 1e-12 && point.lon >= Math.min(x, x2) && point.lon <= Math.max(x, x2) && point.lat >= Math.min(y, y2) && point.lat <= Math.max(y, y2)) return null;
    if ((y > point.lat) !== (y2 > point.lat) && point.lon < (x2 - x) * (point.lat - y) / (y2 - y) + x) contains = !contains;
  }
  return contains;
}
export async function washingtonContains(point: Point): Promise<boolean | null> {
  for (const folder of [resolve(process.cwd(), "..", "data", "environment"), resolve(process.cwd(), "data", "environment")]) {
    try {
      const path = resolve(folder, "washington-boundary.json"); if ((await stat(path)).size > 2_000_000) return null;
      const text = await readFile(path, "utf8"); if (Buffer.byteLength(text) > 2_000_000) return null;
      const evidence = JSON.parse(await readFile(resolve(folder, "washington-boundary.evidence.json"), "utf8"));
      if (evidence.artifact_sha256 !== createHash("sha256").update(text.replace(/\r\n/g, "\n")).digest("hex")) return null;
      const geometry = boundary.parse(JSON.parse(text)).features[0].geometry;
      const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
      for (const rings of polygons) {
        const outer = inside(point, rings[0]); if (outer === null) return null;
        if (outer) { const holes = rings.slice(1).map((r) => inside(point, r)); if (holes.includes(null)) return null; if (!holes.includes(true)) return true; }
      }
      return false;
    } catch { /* Only these two fixed artifact locations are considered. */ }
  }
  return null;
}
