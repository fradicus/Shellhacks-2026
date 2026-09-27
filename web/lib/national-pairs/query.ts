import { z } from "zod";

export const PAGE_SIZE = 50;
export const RULE = "national-provisional-25mi-v1";
const fields = z.object({
  dataset: z.string().regex(/^[a-zA-Z0-9._:-]{1,128}$/),
  scope: z.string().max(160).optional(),
  offset: z.coerce.number().int().min(0).max(1_000_000).default(0),
  id: z.string().regex(/^npc:[a-f0-9]{32}$/).optional(),
}).strict();
export type PairQuery = z.infer<typeof fields>;

export function parseQuery(params: URLSearchParams): PairQuery {
  const input: Record<string, string> = {};
  for (const key of params.keys()) {
    if (params.getAll(key).length !== 1) throw new Error("Duplicate query parameter");
    input[key] = params.get(key)!;
  }
  const query = fields.parse(input);
  if (query.id && (query.scope || query.offset)) throw new Error("A selection cannot include scope or offset");
  pairFilter(query); // validate scope even before any database access
  return query;
}

export function pairFilter(query: PairQuery): Record<string, unknown> {
  const filter: Record<string, unknown> = { dataset: query.dataset, rule_version: RULE };
  if (query.id) filter.id = query.id;
  if (!query.scope) return filter;
  const scope = query.scope;
  if (/^state:\d{2}$/.test(scope)) filter.shared_states = scope.slice(6);
  else if (/^region:[1-4]$/.test(scope)) filter.shared_regions = scope.slice(7);
  else if (/^plan:[a-z0-9-]{1,80}$/.test(scope)) filter.shared_plans = scope.slice(5);
  else {
    const match = scope.match(/^pin:(-?\d{1,3}(?:\.\d+)?),(-?\d{1,3}(?:\.\d+)?)$/);
    if (!match) throw new Error("Invalid scope");
    const lat = Number(match[1]), lon = Number(match[2]);
    if (Math.abs(lat) > 90 || Math.abs(lon) > 180) throw new Error("Invalid pin coordinates");
    // Both centers inside the same 25-mile spherical circle, matching F19 scope.
    const circle = { $geoWithin: { $centerSphere: [[lon, lat], 25 / 3958.8] } };
    filter.geo_a = circle;
    filter.geo_b = circle;
  }
  return filter;
}
