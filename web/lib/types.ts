// Mirrors schemas/*.schema.json. Frozen after F00: additive optional fields only, via a [C<n>] PR.

export type Utility = "DESC" | "GPC" | "unknown";
export type View = "future" | "historical" | "tentative";
export type Confidence = "high" | "medium" | "low" | "rejected";
export type Precision = "day" | "month" | "year" | "unknown";
export type ReviewState = "needs_review" | "confirmed" | "rejected";
export type PublicStatus = "public" | "public_with_banner" | "excluded";

export interface Source {
  _id: string;
  publisher: string;
  title: string;
  sha256: string;
  pages: number | null;
  public_status: PublicStatus;
  url?: string;
  local_path?: string;
  filing?: string;
  retrieved_at?: string;
}

export interface InService {
  raw: string | null;
  /** ISO date; only meaningful as an exact date when precision is "day". */
  date: string | null;
  precision: Precision;
}

export interface Center {
  lat: number;
  lon: number;
  basis?: "two" | "one";
}

export interface Location {
  _id?: string;
  project_key: string;
  endpoint_index: number;
  name: string;
  confidence: Confidence;
  evidence: string;
  lat?: number;
  lon?: number;
  osm_id?: string | null;
  osm_url?: string | null;
}

export interface Project {
  /** `<project_key>@<source_id>` */
  _id: string;
  /** e.g. `DESC:6807B`, `GPC:20277` */
  project_key: string;
  utility: Utility;
  owner_code: string | null;
  native_id: string;
  name: string;
  source: { source_id: string; page: number | null };
  in_service: InService;
  active: boolean;
  status?: string | null;
  voltage_kv?: number | null;
  description?: string | null;
  state?: string;
  owner_basis?: string;
  /** Computed by pipeline/matches/core.py center(); null when no endpoint is located. */
  center?: Center | null;
  location_confidence?: "high" | "medium" | "low" | null;
  geo?: { type: "Point"; coordinates: [number, number] } | null;
  /** Joined from locations (API and fixture mode both join them). */
  endpoints?: Location[];
}

export interface Match {
  /** Sorted project keys joined by `__`. */
  _id: string;
  a: string;
  b: string;
  /** Unrounded miles; round to 2 dp for display only. */
  distance_mi: number;
  time_gap_days: number | null;
  band: 0 | 1;
  rule_version: string;
  rank_version: string;
  analysis_date: string;
  view: View;
  rank?: number;
  review_state?: ReviewState;
}

/** A match with both projects joined (no endpoints), as returned by getMatches and /api/matches. */
export interface MatchRow extends Match {
  project_a: Project | null;
  project_b: Project | null;
}

export interface CitedText {
  text: string;
  fact_ids: string[];
}

export interface Brief {
  _id: string;
  match_id: string;
  input_hash: string;
  model: string;
  prompt_version: string;
  generated_at: string;
  supported_facts: CitedText[];
  possible_shared_activities: CitedText[];
  questions: string[];
  limitations: string[];
  validation: "passed" | "rejected";
  rejection_reason?: string | null;
  facts?: { id: string; [k: string]: unknown }[];
}

export interface Extraction {
  _id: string;
  source_id: string;
  page: number;
  model: string;
  prompt_version: string;
  fields: Record<string, unknown>;
  comparison: Record<string, unknown>;
  accepted: boolean;
  generated_at?: string;
  schema_version?: string;
}

export interface Review {
  _id: string;
  record_id: string;
  verdict: string;
  reason: string;
  reviewer: string;
  at: string;
}

export interface Run {
  _id: string;
  stage: string;
  started_at: string;
  finished_at: string | null;
  status: "ok" | "failed" | "partial";
  counts: Record<string, unknown>;
}

export interface Coverage {
  /** source_id */
  _id: string;
  counts: Record<string, unknown>;
}

export interface VersionChange {
  _id: string;
  project_key: string;
  from_source: string;
  to_source: string;
  field: string;
  old: unknown;
  new: unknown;
  from_page?: number | null;
  to_page?: number | null;
}

/** Response of getPair and /api/pairs/[id]. */
export interface PairDetail {
  match: Match;
  /** Projects with endpoints joined. */
  a: Project | null;
  b: Project | null;
  /** Only a brief whose validation passed; otherwise null. */
  brief: Brief | null;
  version_changes: VersionChange[];
  reviews?: Review[];
}

export interface Unavailable {
  unavailable: true;
  reason: string;
}

export type Result<T> = T | Unavailable;

export function isUnavailable<T>(r: Result<T>): r is Unavailable {
  return typeof r === "object" && r !== null && (r as Unavailable).unavailable === true;
}
