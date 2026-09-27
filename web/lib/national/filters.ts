import { z } from "zod";
import type {
  NationalFilterAction,
  NationalFilters,
  NationalGeography,
  NationalProject,
  NationalStatus,
} from "./types";

export const DEFAULT_LIMIT = 50;
export const MAX_LIMIT = 100;
export const MAX_EXPORT = 2_000;
export const MAX_MAP_POINTS = 10_000;
export const MAX_DATASET_PROJECTS = 10_000;

const CODE = {
  region: /^[1-4]$/,
  state: /^\d{2}$/,
  county: /^\d{5}$/,
};

const DateValue = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine((value) => {
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.valueOf()) && date.toISOString().slice(0, 10) === value;
}, "must be a real ISO date");

const OptionalTrimmed = (max: number) => z.string().trim().min(1).max(max).optional();

export const NationalQuery = z.strictObject({
  region: z.string().regex(CODE.region).optional(),
  state: z.string().regex(CODE.state).optional(),
  county: z.string().regex(CODE.county).optional(),
  planningregion: OptionalTrimmed(80),
  owner: OptionalTrimmed(160),
  status: z.enum(["planned", "under_construction", "proposed", "in_service", "cancelled", "unknown"]).optional(),
  from: DateValue.optional(),
  to: DateValue.optional(),
  text: OptionalTrimmed(120),
  view: z.enum(["map", "mindmap"]).optional(),
  page: z.coerce.number().int().min(1).max(10_000).default(1),
  limit: z.coerce.number().int().min(1).max(MAX_LIMIT).default(DEFAULT_LIMIT),
});

export function parseNationalFilters(raw: Record<string, string | string[] | undefined>): NationalFilters {
  const scalar = Object.fromEntries(
    Object.entries(raw).map(([key, value]) => [key, Array.isArray(value) ? value[value.length - 1] : value]),
  );
  const parsed = NationalQuery.safeParse(scalar);
  if (!parsed.success) throw new Error(parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`).join("; "));
  if (parsed.data.from && parsed.data.to && parsed.data.from > parsed.data.to) throw new Error("from must not be after to");
  return {
    region: parsed.data.region,
    state: parsed.data.state,
    county: parsed.data.county,
    planningRegion: parsed.data.planningregion,
    owner: parsed.data.owner,
    status: parsed.data.status,
    from: parsed.data.from,
    to: parsed.data.to,
    text: parsed.data.text,
    view: parsed.data.view,
    page: parsed.data.page,
    limit: parsed.data.limit,
  };
}

export function validateGeographyFilters(filters: NationalFilters, geography: NationalGeography | null): string | null {
  if (!geography) return filters.region || filters.state || filters.county ? "reference geography unavailable" : null;
  const state = filters.state ? geography.states.find((item) => item.state_fips === filters.state) : undefined;
  const county = filters.county ? geography.counties.find((item) => item.county_geoid === filters.county) : undefined;
  if (filters.state && !state) return "unknown state FIPS";
  if (filters.county && !county) return "unknown county GEOID";
  if (state && filters.region && state.census_region_code !== filters.region) return "state is not in the selected Census region";
  if (county && filters.state && county.state_fips !== filters.state) return "county is not in the selected state";
  if (county && filters.region) {
    const parent = geography.states.find((item) => item.state_fips === county.state_fips);
    if (parent?.census_region_code !== filters.region) return "county is not in the selected Census region";
  }
  return null;
}

function interval(project: NationalProject): [string, string] | null {
  const { value, precision } = project.in_service;
  if (!value || precision === "unknown") return null;
  if (precision === "day") return [value, value];
  if (precision === "month") {
    const [year, month] = value.split("-").map(Number);
    const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
    return [`${value}-01`, `${value}-${String(last).padStart(2, "0")}`];
  }
  return [`${value}-01-01`, `${value}-12-31`];
}

export function filterNationalProjects(projects: NationalProject[], filters: NationalFilters, geography: NationalGeography | null): NationalProject[] {
  const stateCodes = filters.region
    ? new Set(geography?.states.filter((state) => state.census_region_code === filters.region).map((state) => state.state_fips) ?? [])
    : null;
  const needle = filters.text?.toLocaleLowerCase("en-US");
  return projects.filter((project) => {
    if (stateCodes && !project.states.some((code) => stateCodes.has(code))) return false;
    if (filters.state && !project.states.includes(filters.state)) return false;
    if (filters.county && !project.counties.includes(filters.county)) return false;
    if (filters.planningRegion && project.planning_region !== filters.planningRegion) return false;
    if (filters.owner && project.owner !== filters.owner && !project.other_owners.includes(filters.owner)) return false;
    if (filters.status && project.status_group !== filters.status) return false;
    if (filters.from || filters.to) {
      const range = interval(project);
      if (!range || (filters.from && range[1] < filters.from) || (filters.to && range[0] > filters.to)) return false;
    }
    if (needle) {
      const fields = [project.name, project.native_id, project.description, project.owner, project.planning_region, project.status]
        .filter((value): value is string => typeof value === "string");
      if (!fields.some((value) => value.toLocaleLowerCase("en-US").includes(needle))) return false;
    }
    return true;
  });
}

export function serializeNationalFilters(filters: NationalFilters): string {
  const params = new URLSearchParams();
  const entries: [string, string | number | undefined][] = [
    ["region", filters.region], ["state", filters.state], ["county", filters.county],
    ["planningregion", filters.planningRegion], ["owner", filters.owner], ["status", filters.status],
    ["from", filters.from], ["to", filters.to], ["text", filters.text],
    ["view", filters.view && filters.view !== "map" ? filters.view : undefined],
    ["page", filters.page === 1 ? undefined : filters.page], ["limit", filters.limit === DEFAULT_LIMIT ? undefined : filters.limit],
  ];
  for (const [key, value] of entries) if (value !== undefined && value !== "") params.set(key, String(value));
  return params.toString();
}

export function cascadeFilters(current: NationalFilters, patch: Partial<Omit<NationalFilters, "page" | "limit">>): NationalFilters {
  const next = { ...current, ...patch, page: 1 };
  if ("region" in patch && patch.region !== current.region) {
    if (!("state" in patch)) next.state = undefined;
    if (!("county" in patch)) next.county = undefined;
  } else if ("state" in patch && patch.state !== current.state) {
    if (!("county" in patch)) next.county = undefined;
  }
  return next;
}

export function applyFilterAction(current: NationalFilters, action: NationalFilterAction): NationalFilters | null {
  if (action.type === "filters.reset") return { page: 1, limit: current.limit, view: current.view ?? "map" };
  if (action.type === "filters.patch") return cascadeFilters(current, action.filters);
  if (action.type === "filters.clear") {
    const patch = Object.fromEntries(action.keys.map((key) => [key, undefined]));
    return cascadeFilters(current, patch);
  }
  if (action.type === "geography.focus") {
    if (action.kind === "region") return cascadeFilters(current, { region: action.code });
    if (action.kind === "state") return cascadeFilters(current, { state: action.code });
    return cascadeFilters(current, { county: action.code });
  }
  return null;
}

export const STATUS_LABEL: Record<NationalStatus, string> = {
  planned: "Planned",
  under_construction: "Under construction",
  proposed: "Proposed",
  in_service: "In service",
  cancelled: "Cancelled",
  unknown: "Status unknown",
};
