import { z } from "zod";
import { DbUnavailable } from "./db";
import { DeadlineExceeded } from "./deadline";

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

/** A read failure as a status and a public reason. Never the exception text: it can carry hostnames. */
export function readFailure(err: unknown): { status: 503 | 504; reason: string } {
  if (err instanceof DeadlineExceeded) return { status: 504, reason: "database timed out" };
  if (err instanceof DbUnavailable) return { status: 503, reason: err.message };
  return { status: 503, reason: "database error" };
}

/**
 * Parse query params strictly (unknown params -> 400), then run `fn` through the shared repository with the
 * request's abort signal, so a client that goes away cancels its queries.
 * Unavailable -> 503 {unavailable: true}; total deadline -> 504 {unavailable: true}; never fixtures.
 */
export async function handleRead<T>(
  req: Request,
  schema: z.ZodType<T>, // build with z.strictObject so unknown params fail
  fn: (q: T, signal: AbortSignal) => Promise<unknown>,
): Promise<Response> {
  const params = Object.fromEntries(new URL(req.url).searchParams);
  const parsed = schema.safeParse(params);
  if (!parsed.success) {
    return json({ error: "invalid query", issues: parsed.error.issues.map((i) => `${i.path.join(".") || "query"}: ${i.message}`) }, 400);
  }
  try {
    const body = await fn(parsed.data, req.signal);
    return body === null ? json({ error: "not found" }, 404) : json(body);
  } catch (err) {
    const { status, reason } = readFailure(err);
    console.error(`api ${new URL(req.url).pathname}: ${reason}${err instanceof DbUnavailable || err instanceof DeadlineExceeded ? "" : ` (${(err as Error)?.name})`}`);
    return json({ unavailable: true, reason }, status);
  }
}
