import { z } from "zod";

// Provider outputs and offline commands must pass this same bounded action boundary.
// This module never executes code, fetches URLs, or accepts a database expression.
const Status = z.enum(["planned", "under_construction", "proposed", "in_service", "cancelled", "unknown"]);
const Filters = z.strictObject({
  region: z.string().regex(/^[1-4]$/).optional(),
  state: z.string().regex(/^\d{2}$/).optional(),
  county: z.string().regex(/^\d{5}$/).optional(),
  planningRegion: z.string().trim().min(1).max(80).optional(),
  owner: z.string().trim().min(1).max(160).optional(),
  status: Status.optional(),
  text: z.string().trim().min(1).max(120).optional(),
});

export const AssistantActionSchema = z.discriminatedUnion("type", [
  z.strictObject({ type: z.literal("filters.patch"), filters: Filters }),
  z.strictObject({ type: z.literal("filters.reset") }),
  z.strictObject({ type: z.literal("project.select"), projectId: z.string().min(1).max(240) }),
  z.strictObject({ type: z.literal("geography.focus"), kind: z.enum(["state", "county", "region"]), code: z.string().min(1).max(5) }),
  z.strictObject({ type: z.literal("navigate"), view: z.enum(["overlaps", "time", "coverage", "changes", "explore"]) }),
]);

export type AssistantAction = z.infer<typeof AssistantActionSchema>;
export type AssistantFilters = z.infer<typeof Filters>;
export interface AssistantContext {
  states: ReadonlyArray<{ state_fips: string; name: string; usps: string; census_region_code: string | null }>;
  counties: ReadonlyArray<{ county_geoid: string; name: string; full_name: string; state_fips: string; state_name: string }>;
  regions: ReadonlyArray<{ region_code: string; name: string }>;
  planningRegions: readonly string[];
  owners: readonly string[];
  visibleProjectIds: readonly string[];
}
export type CommandResult =
  | { ok: true; action: AssistantAction; summary: string }
  | { ok: false; kind: "clarification" | "unsupported" | "invalid"; message: string };

export const APPROVED_VIEWS = {
  overlaps: "/", time: "/time", coverage: "/coverage", changes: "/changes", explore: "/assistant",
} as const;

const fold = (text: string) => text.normalize("NFKC").trim().replace(/\s+/g, " ").toLocaleLowerCase("en-US");

/** Validate again immediately before execution; result IDs may have changed since a model answered. */
export function validateAssistantAction(value: unknown, context: AssistantContext): AssistantAction {
  const action = AssistantActionSchema.parse(value);
  if (action.type === "project.select" && !context.visibleProjectIds.includes(action.projectId)) {
    throw new Error("That project is no longer in the visible results. Search for it first.");
  }
  if (action.type === "geography.focus") {
    const exists = action.kind === "state"
      ? context.states.some((item) => item.state_fips === action.code)
      : action.kind === "county"
        ? context.counties.some((item) => item.county_geoid === action.code)
        : context.regions.some((item) => item.region_code === action.code);
    if (!exists) throw new Error("That geography is not in the current Census reference.");
  }
  if (action.type === "filters.patch") {
    const filters = action.filters;
    if (!Object.keys(filters).length) throw new Error("No supported filter change was provided.");
    const state = context.states.find((item) => item.state_fips === filters.state);
    const county = context.counties.find((item) => item.county_geoid === filters.county);
    if (filters.state && !state) throw new Error("Unknown state.");
    if (filters.county && !county) throw new Error("Unknown county.");
    if (filters.region && !context.regions.some((item) => item.region_code === filters.region)) throw new Error("Unknown Census region.");
    if (state && filters.region && state.census_region_code !== filters.region) throw new Error("State and Census region disagree.");
    if (county && filters.state && county.state_fips !== filters.state) throw new Error("County and state disagree.");
    if (county && filters.region && context.states.find((item) => item.state_fips === county.state_fips)?.census_region_code !== filters.region) {
      throw new Error("County and Census region disagree.");
    }
    if (filters.planningRegion && !context.planningRegions.includes(filters.planningRegion)) throw new Error("Unknown planning region.");
    if (filters.owner && !context.owners.includes(filters.owner)) throw new Error("Unknown owner in this dataset.");
  }
  return action;
}

function result(action: AssistantAction, summary: string, context: AssistantContext): CommandResult {
  try {
    return { ok: true, action: validateAssistantAction(action, context), summary };
  } catch (error) {
    return { ok: false, kind: "invalid", message: error instanceof Error ? error.message : "Unsupported action." };
  }
}

function place(text: string, context: AssistantContext):
  | { filters: AssistantFilters; label: string; kind: "state" | "county" | "region"; code: string }
  | { problem: string } {
  const normalized = fold(text);
  const state = context.states.find((item) => fold(item.name) === normalized || fold(item.usps) === normalized);
  if (state) return { filters: { region: state.census_region_code ?? undefined, state: state.state_fips }, label: state.name, kind: "state", code: state.state_fips };
  const region = context.regions.find((item) => fold(item.name).replace(/ region$/, "") === normalized.replace(/ region$/, ""));
  if (region) return { filters: { region: region.region_code }, label: `${region.name.replace(/ Region$/, "")} Census region`, kind: "region", code: region.region_code };

  // Require the state when the same county name occurs in more than one place.
  const qualified = normalized.match(/^(.+?)(?:\s+in\s+|,\s*)(.+)$/);
  const countyName = qualified?.[1] ?? normalized;
  const parentName = qualified?.[2];
  const parent = parentName ? context.states.find((item) => fold(item.name) === parentName || fold(item.usps) === parentName) : null;
  if (parentName && !parent) return { problem: `I could not identify the state “${parentName}”. Use its full name or postal code.` };
  const counties = context.counties.filter((item) =>
    (fold(item.name) === countyName || fold(item.full_name) === countyName) && (!parent || item.state_fips === parent.state_fips),
  );
  if (counties.length === 1) {
    const county = counties[0];
    return {
      filters: {
        region: context.states.find((item) => item.state_fips === county.state_fips)?.census_region_code ?? undefined,
        state: county.state_fips, county: county.county_geoid,
      },
      label: `${county.full_name}, ${county.state_name}`, kind: "county", code: county.county_geoid,
    };
  }
  if (counties.length > 1) {
    const names = [...new Set(counties.map((item) => item.state_name))].slice(0, 6).join(", ");
    return { problem: `Which state? “${text}” occurs in ${names}${counties.length > 6 ? ", and others" : ""}.` };
  }
  return { problem: `I could not identify “${text}” as a state, county, or Census region. Try “show projects in Massachusetts”.` };
}

/** Explicit offline command preview. It does not call or simulate a language model. */
export function parseOfflineCommand(input: string, context: AssistantContext): CommandResult {
  if (!input.trim() || input.length > 500) return { ok: false, kind: "invalid", message: "Enter a command of 1–500 characters." };
  const command = fold(input).replace(/[.!?]$/, "");
  if (/^(reset|clear filters|show all projects)$/.test(command)) {
    return result({ type: "filters.reset" }, "Reset all project filters.", context);
  }
  const navigation = command.match(/^(?:go to|open) (overlaps|time|coverage|changes|explore)$/);
  if (navigation) {
    const view = navigation[1] as keyof typeof APPROVED_VIEWS;
    return result({ type: "navigate", view }, `Open ${view}.`, context);
  }
  const project = input.trim().match(/^select project\s+(.+)$/i);
  if (project) return result({ type: "project.select", projectId: project[1].trim() }, "Select the project in the current results.", context);
  const find = input.trim().match(/^find\s+"([^"]+)"[.!?]?$/i);
  if (find) return result({ type: "filters.patch", filters: { text: find[1] } }, `Search source text for “${find[1]}”.`, context);
  const focus = command.match(/^(?:focus|zoom to) (.+)$/);
  if (focus) {
    const target = place(focus[1], context);
    if ("problem" in target) return { ok: false, kind: "clarification", message: target.problem };
    return result({ type: "geography.focus", kind: target.kind, code: target.code }, `Focus the map on ${target.label}. Reference bounds do not locate projects.`, context);
  }
  const planning = command.match(/^show planning region (.+)$/);
  if (planning) {
    const region = context.planningRegions.find((item) => fold(item) === planning[1]);
    if (!region) return { ok: false, kind: "clarification", message: "Use a planning region with imported project records, shown in the planning region filter. Catalog-only regions are not imported." };
    return result({ type: "filters.patch", filters: { planningRegion: region } }, `Filter the publishing planning region to ${region}.`, context);
  }
  const show = command.match(/^show (?:(planned|proposed|under construction|in service|cancelled|unknown) )?projects in (.+)$/);
  if (show) {
    const target = place(show[2], context);
    if ("problem" in target) return { ok: false, kind: "clarification", message: target.problem };
    const status = show[1]?.replaceAll(" ", "_") as AssistantFilters["status"];
    return result(
      { type: "filters.patch", filters: { ...target.filters, ...(status ? { status } : {}) } },
      `Show ${show[1] ? `${show[1]} ` : ""}projects in ${target.label}. Other filters stay as displayed.`, context,
    );
  }
  return {
    ok: false, kind: "unsupported",
    message: "This offline preview supports explicit filter, focus, search and navigation commands. General questions require a connected model. Try “show projects in Massachusetts”, “focus California”, or “reset”.",
  };
}
