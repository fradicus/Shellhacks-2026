import type { NationalProject } from "./types";

export interface DisplayPoint { lat: number; lon: number; county_geoid?: string; county_name?: string }
const validPoint = (p: DisplayPoint) => Number.isFinite(p.lat) && Math.abs(p.lat) <= 90
  && Number.isFinite(p.lon) && Math.abs(p.lon) <= 180;

/** Display coordinates only. Never replace the stored project center with an area reference. */
export function displayPoints(project: NationalProject): DisplayPoint[] {
  if (project.location_review === "rejected") return [];
  if (project.center && project.location_review !== "unlocated") return validPoint(project.center) ? [project.center] : [];
  const area = project.approximate_location;
  if (project.center !== null || area?.precision !== "county" || area.eligible_for_matching !== false
    || !area.reference_source?.url || !Array.isArray(area.anchors)) return [];
  return area.anchors.filter((point) => project.counties.includes(point.county_geoid) && validPoint(point));
}

export function locationLabel(project: NationalProject): string {
  if (!displayPoints(project).length) return "Location unknown";
  if (!project.center) return "County reference — exact site unknown";
  return project.location_review === "confirmed" ? "Confirmed location" : "Tentative location";
}
