import type { NationalProject, NationalSource } from "@/lib/national/types";
import type { TimeProject } from "./TimeView";

/** /time plans; /history keeps the record. A national record its publisher lists as in service belongs to History,
 * and drawing 2001-2025 completions here stretched the planning axis over 25 years of past. */
export const stillPlanned = (p: TimeProject) => p.national?.project.status_group !== "in_service";

/** C25 display tiers: an independently confirmed location, or the unreviewed official/candidate point its release
 * declared. Candidate points are drawn with their own colour and label and never enter pairs or overlaps. */
const DRAWN = new Set<NationalProject["location_review"]>(["confirmed", "unreviewed"]);
export const CANDIDATE_COLOR = "#d9c38c";

export function locationLabel(project: NationalProject): string {
  if (project.location_review === "confirmed") return "Location confirmed";
  const tier = (project as NationalProject & { location_candidate?: { tier?: string | null } }).location_candidate?.tier;
  return tier === "official" ? "Official source location, not independently reviewed"
    : tier === "candidate_unique_name" ? "Candidate location (name match only), not independently reviewed"
    : "Candidate location, not independently reviewed";
}

/** The national collection also projects legacy filing versions; F19 already selects those itself. */
export const drawnNational = (project: NationalProject) => !project._id.startsWith("legacy:")
  && DRAWN.has(project.location_review) && !!project.center
  && Number.isFinite(project.center.lat) && Math.abs(project.center.lat) <= 90
  && Number.isFinite(project.center.lon) && Math.abs(project.center.lon) <= 180;

export function nationalTimeProjects(projects: NationalProject[], sources: NationalSource[]): TimeProject[] {
  const sourceById = new Map(sources.map((source) => [source._id, source]));
  return projects.filter(drawnNational)
    .map((project) => ({
      key: project._id,
      name: project.name,
      utility: "unknown",
      owner_code: null,
      center: project.center,
      in_service: { date: project.in_service.value, precision: project.in_service.precision, raw: project.in_service.raw },
      confidence: null,
      source_id: project.source_id,
      page: project.evidence.page,
      national: { project, source: sourceById.get(project.source_id) },
    }));
}
