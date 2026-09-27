import type { Brief, Match, Project } from "@/lib/types";

type Cell = string | number | boolean | null | undefined;
const FORMULA_START = /^[=+\-@\t\r]/;

function cell(value: Cell): string {
  if (value === null || value === undefined) return "";
  let text = typeof value === "number" ? (Number.isFinite(value) ? String(value) : "") : String(value);
  if (typeof value !== "number" && FORMULA_START.test(text)) text = `'${text}`;
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function projectCells(prefix: "a" | "b", project: Project | null, key: string): [string, Cell][] {
  return [
    [`${prefix}_project_key`, key],
    [`${prefix}_project_version_id`, project?._id ?? null],
    [`${prefix}_utility`, project?.utility ?? "unknown"],
    [`${prefix}_native_id`, project?.native_id ?? null],
    [`${prefix}_name`, project?.name ?? null],
    [`${prefix}_owner_code`, project?.owner_code ?? "not published"],
    [`${prefix}_status`, project?.status ?? "not published"],
    [`${prefix}_in_service_raw`, project?.in_service.raw ?? null],
    [`${prefix}_in_service_date`, project?.in_service.date ?? null],
    [`${prefix}_in_service_precision`, project?.in_service.precision ?? "unknown"],
    [`${prefix}_location_confidence`, project?.location_confidence ?? "needs review"],
    [`${prefix}_center_lat`, project?.center?.lat ?? null],
    [`${prefix}_center_lon`, project?.center?.lon ?? null],
    [`${prefix}_center_basis`, project?.center?.basis ?? "no center"],
    [`${prefix}_source_id`, project?.source.source_id ?? null],
    [`${prefix}_source_page`, project?.source.page ?? null],
  ];
}

/** Export the displayed pair and its source versions, without refetching another dataset/view. */
export function pairCsv(match: Match, a: Project | null, b: Project | null, brief: Brief | null): string {
  const entries: [string, Cell][] = [
    ["pair_id", match._id],
    ["view", match.view],
    ["rank", match.rank ?? null],
    ["review_state", match.review_state ?? "needs_review"],
    ["band", match.band === 0 ? "<10 mi" : "10-25 mi"],
    ["distance_mi_unrounded", match.distance_mi],
    ["distance_mi_2dp", match.distance_mi.toFixed(2)],
    ["time_gap_days", match.time_gap_days ?? "unknown"],
    ["analysis_date", match.analysis_date],
    ["rule_version", match.rule_version],
    ["rank_version", match.rank_version],
    ...projectCells("a", a, match.a),
    ...projectCells("b", b, match.b),
    ["gemini_brief", brief ? "validated" : "unavailable"],
    ["gemini_model", brief?.model ?? null],
    ["gemini_prompt_version", brief?.prompt_version ?? null],
    ["gemini_generated_at", brief?.generated_at ?? null],
  ];
  return `${entries.map(([name]) => cell(name)).join(",")}\r\n${entries.map(([, value]) => cell(value)).join(",")}\r\n`;
}

export function pairCsvFilename(pairId: string): string {
  const safe = pairId.replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "pair";
  return `gridbridge-pair-${safe}.csv`;
}
