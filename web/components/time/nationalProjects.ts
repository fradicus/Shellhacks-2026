import type { NationalProjectSummary } from "@/lib/national/types";
import type { TimeProject } from "./TimeView";

/** /time plans; /history keeps the record. A national record its publisher lists as in service belongs to History,
 * and drawing 2001-2025 completions here stretched the planning axis over 25 years of past. */
export const stillPlanned = (p: TimeProject) => p.national?.project.status_group !== "in_service";

/** How a drawn national point was located (C25): independently reviewed, the owner's own published coordinate, or a
 * labeled tentative match. Rejected, stale and unlocated records are never drawn. */
export type NationalTier = "confirmed" | "official" | "tentative";
export function nationalTier(project: NationalProjectSummary): NationalTier | null {
  if (project.location_review === "confirmed") return "confirmed";
  if (project.location_review !== "unreviewed") return null;
  const tier = project.location_candidate?.tier;
  return tier === "official" ? "official" : "tentative";
}

/** The national collection also projects legacy filing versions; F19 already selects those itself. */
export function nationalTimeProjects(projects: NationalProjectSummary[]): TimeProject[] {
  return projects.filter((project) => !project._id.startsWith("legacy:")
    && nationalTier(project) !== null && project.center
    && Number.isFinite(project.center.lat) && Math.abs(project.center.lat) <= 90
    && Number.isFinite(project.center.lon) && Math.abs(project.center.lon) <= 180)
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
      national: { project, tier: nationalTier(project)! },
    }));
}
