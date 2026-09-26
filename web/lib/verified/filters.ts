import { z } from "zod";
import type { VerifiedFilters, VerifiedUtilityRecord } from "./types";

export const VERIFIED_DEFAULT_LIMIT = 25;
export const VERIFIED_MAX_LIMIT = 100;
const ALLOWED = new Set(["state", "county", "q", "page", "limit"]);

const Query = z.strictObject({
  state: z.string().regex(/^\d{2}$/).optional(),
  county: z.string().regex(/^\d{5}$/).optional(),
  q: z.string().trim().min(1).max(120).optional(),
  page: z.coerce.number().int().min(1).max(10_000).default(1),
  limit: z.coerce.number().int().min(1).max(VERIFIED_MAX_LIMIT).default(VERIFIED_DEFAULT_LIMIT),
});

export function parseVerifiedParams(params: URLSearchParams): VerifiedFilters {
  const raw: Record<string, string> = {};
  for (const key of params.keys()) {
    if (!ALLOWED.has(key)) throw new Error(`${key}: unknown parameter`);
    if (params.getAll(key).length !== 1) throw new Error(`${key}: duplicate parameter`);
    raw[key] = params.get(key)!;
  }
  const parsed = Query.safeParse(raw);
  if (!parsed.success) throw new Error(parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`).join("; "));
  if (parsed.data.county && !parsed.data.state) throw new Error("county requires its parent state");
  return parsed.data;
}

export function validateVerifiedGeography(
  filters: VerifiedFilters,
  geography: { states: { state_fips: string }[]; counties: { county_geoid: string; state_fips: string }[] },
): string | null {
  if (filters.state && !geography.states.some((item) => item.state_fips === filters.state)) return "unknown state FIPS";
  if (filters.county) {
    const county = geography.counties.find((item) => item.county_geoid === filters.county);
    if (!county) return "unknown county GEOID";
    if (county.state_fips !== filters.state) return "county is not in the selected state";
  }
  return null;
}

export function filterVerifiedUtilities(records: VerifiedUtilityRecord[], filters: VerifiedFilters): VerifiedUtilityRecord[] {
  const needle = filters.q?.toLocaleLowerCase("en-US");
  return records.filter((record) => {
    if (filters.state && !record.state_fips.includes(filters.state)) return false;
    if (filters.county && !record.county_geoids.includes(filters.county)) return false;
    if (needle && !record.eia_utility_id.toLocaleLowerCase("en-US").includes(needle)
      && !record.name.toLocaleLowerCase("en-US").includes(needle)) return false;
    return true;
  });
}
