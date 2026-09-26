import type { Db } from "mongodb";
import { z } from "zod";
import { activeDataset, DbUnavailable, getDb } from "./db";

export const VIEW = z.enum(["future", "historical", "tentative"]);

export type BBox = [west: number, south: number, east: number, north: number];

/** `w,s,e,n` in degrees within +/-180/90; west < east (no antimeridian crossing), south < north. */
export const BBOX = z.string().transform((raw, ctx): BBox => {
  const v = raw.split(",").map(Number);
  const [w, s, e, n] = v;
  const ok = v.length === 4 && v.every(Number.isFinite) && w >= -180 && e <= 180 && s >= -90 && n <= 90 && w < e && s < n;
  if (!ok) ctx.addIssue({ code: "custom", message: "bbox must be west,south,east,north within ±180/±90 with west < east, south < north" });
  return ok ? [w, s, e, n] : [0, 0, 0, 0];
});

export const LIMIT = z.coerce.number().int().min(1).max(500);
export const MAX_DISTANCE = z.coerce.number().finite().min(0).max(25);

const json = (body: unknown, status = 200) =>
  Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

/**
 * Parse query params strictly (unknown params -> 400), open the active dataset, run `fn`.
 * Database problems -> 503 {unavailable: true}; never fixtures.
 */
export function handle<T>(
  req: Request,
  schema: z.ZodType<T>, // build with z.strictObject so unknown params fail
  fn: (q: T, db: Db, dataset: string) => Promise<unknown>,
): Promise<Response> {
  return handleDb(req, schema, async (q, db) => fn(q, db, await activeDataset(db)));
}

/** `handle` without requiring an active dataset: only for data that isn't dataset-scoped (runs). */
export async function handleDb<T>(
  req: Request,
  schema: z.ZodType<T>,
  fn: (q: T, db: Db) => Promise<unknown>,
): Promise<Response> {
  const params = Object.fromEntries(new URL(req.url).searchParams);
  const parsed = schema.safeParse(params);
  if (!parsed.success) {
    return json({ error: "invalid query", issues: parsed.error.issues.map((i) => `${i.path.join(".") || "query"}: ${i.message}`) }, 400);
  }
  try {
    const db = await getDb();
    const body = await fn(parsed.data, db);
    return body === null ? json({ error: "not found" }, 404) : json(body);
  } catch (err) {
    const reason = err instanceof DbUnavailable ? err.message : "database error";
    console.error(`api ${new URL(req.url).pathname}: ${reason}${err instanceof DbUnavailable ? "" : ` (${(err as Error)?.name})`}`);
    return json({ unavailable: true, reason }, 503);
  }
}
