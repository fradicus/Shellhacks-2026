import type { NationalProject, NationalSource } from "@/lib/national/types";
import type { TimeProject } from "./TimeView";

/** The national collection also projects legacy filing versions; F19 already selects those itself. */
export function nationalTimeProjects(projects: NationalProject[], sources: NationalSource[]): TimeProject[] {
  const sourceById = new Map(sources.map((source) => [source._id, source]));
  return projects.filter((project) => !project._id.startsWith("legacy:")
    && project.location_review === "confirmed" && project.center
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
      national: { project, source: sourceById.get(project.source_id) },
    }));
}
