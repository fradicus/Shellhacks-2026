import type { NationalProject, NationalProjectSummary } from "./types";

/** Explicit allowlist: new producer evidence never leaks into initial page props. */
export function projectSummary(p: NationalProject): NationalProjectSummary {
  return {
    _id: p._id, source_id: p.source_id, native_id: p.native_id, name: p.name,
    owner: p.owner, other_owners: p.other_owners, planning_region: p.planning_region,
    states: p.states, counties: p.counties, geography_basis: p.geography_basis,
    status: p.status, status_group: p.status_group, in_service: p.in_service,
    location_review: p.location_review, approximate_location: p.approximate_location,
    center: p.center ? { lat: p.center.lat, lon: p.center.lon, basis: p.center.basis } : null,
    evidence: { page: p.evidence.page, sheet: p.evidence.sheet, row: p.evidence.row },
    location_candidate: p.location_candidate ? { tier: p.location_candidate.tier, label: p.location_candidate.label } : undefined,
  };
}
