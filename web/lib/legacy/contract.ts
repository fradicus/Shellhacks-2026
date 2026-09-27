// The legacy overlap result contract: one description of "what the user is looking at" shared by /map (URL state,
// map, pair list, project table) and /api/export. Pure and client-safe.
import type { MatchRow, Project, View } from "../types";

export const VIEWS = ["future", "historical", "tentative"] as const satisfies readonly View[];

/** current: one record per project key, the active filing's. all_versions: every filing version on record. */
export const RECORD_MODES = ["current", "all_versions"] as const;
export type RecordMode = (typeof RECORD_MODES)[number];

export type ResultSelection = { kind: "pair"; id: string } | { kind: "project"; key: string } | null;

export interface LegacyResult {
  view: View;
  records: RecordMode;
  selection: ResultSelection;
}

/** Rows per export page. An export never silently drops rows: past this it is paged, and says so. */
export const EXPORT_PAGE_SIZE = 5_000;

const KEY = /^[A-Za-z0-9:._\- ]{1,300}$/;

type Params = URLSearchParams | Record<string, string | string[] | undefined>;
const read = (params: Params, key: string): string | undefined => {
  const value = params instanceof URLSearchParams ? params.get(key) ?? undefined : params[key];
  return Array.isArray(value) ? value[value.length - 1] : value;
};

/** Reads a result from URL params. Unknown or malformed values fall back to defaults instead of failing the page. */
export function parseLegacyResult(params: Params, fallbackView: View): LegacyResult {
  const view = read(params, "view");
  const records = read(params, "records");
  const pair = read(params, "pair");
  const project = read(params, "project");
  return {
    view: (VIEWS as readonly string[]).includes(view ?? "") ? (view as View) : fallbackView,
    records: records === "all_versions" ? "all_versions" : "current",
    selection: pair && KEY.test(pair) ? { kind: "pair", id: pair } : project && KEY.test(project) ? { kind: "project", key: project } : null,
  };
}

/** URL params for a result; defaults are left out so a plain /map stays plain. */
export function serializeLegacyResult(result: LegacyResult, defaultView: View): URLSearchParams {
  const params = new URLSearchParams();
  if (result.view !== defaultView) params.set("view", result.view);
  if (result.records !== "current") params.set("records", result.records);
  if (result.selection?.kind === "pair") params.set("pair", result.selection.id);
  if (result.selection?.kind === "project") params.set("project", result.selection.key);
  return params;
}

/** The export of exactly this result: the same view, record mode and selection. */
export function exportHref(type: "matches" | "projects", result: LegacyResult): string {
  const params = new URLSearchParams({ type });
  if (type === "matches") params.set("view", result.view);
  if (type === "projects") params.set("records", result.records);
  if (result.selection?.kind === "project") params.set("project", result.selection.key);
  if (type === "matches" && result.selection?.kind === "pair") params.set("pair", result.selection.id);
  return `/api/export?${params}`;
}

/** One current record per project key: the active filing's (ties or none -> smallest _id). The single rule /map,
 * /time, History and the export all use, so an older filing never shows up as a second current project. */
export function currentProjects(projects: Project[]): { current: Project[]; superseded: number } {
  const byKey = new Map<string, Project>();
  for (const p of [...projects].sort((a, b) => Number(b.active) - Number(a.active) || a._id.localeCompare(b._id))) {
    if (!byKey.has(p.project_key)) byKey.set(p.project_key, p);
  }
  return { current: [...byKey.values()], superseded: projects.length - byKey.size };
}

/** The project rows a record mode shows, in the table's order. */
export function projectRecords(projects: Project[], records: RecordMode): Project[] {
  const rows = records === "current" ? currentProjects(projects).current : [...projects];
  return rows.sort((a, b) => a.utility.localeCompare(b.utility) || a.name.localeCompare(b.name) || a._id.localeCompare(b._id));
}

/** Pairs a result covers: its view, narrowed to one project's pairs or one pair when that is selected. */
export function resultMatches(matches: MatchRow[], result: Pick<LegacyResult, "view" | "selection">): MatchRow[] {
  const sel = result.selection;
  return matches.filter((m) => m.view === result.view
    && (sel?.kind !== "project" || m.a === sel.key || m.b === sel.key)
    && (sel?.kind !== "pair" || m._id === sel.id));
}

/** What an export response states about itself, in headers and in `format=manifest`. */
export interface ExportManifest {
  type: "matches" | "projects";
  release: string;
  mode: "fixture" | "atlas";
  filters: { view: View | null; records: RecordMode | null; project: string | null; pair: string | null };
  total: number;
  page: number;
  pages: number;
  page_size: number;
  returned: number;
  /** True when more rows exist than this response carries; `next` fetches them. */
  truncated: boolean;
  next: string | null;
}
