import { loadNationalExplorer } from "@/lib/national/server";
import { nationalTimeProjects, stillPlanned } from "@/components/time/nationalProjects";
import { TimeView, type TimePair, type TimeProject } from "@/components/time/TimeView";
import { ErrorState } from "@/components/ui";
import { analysisDate, getMatches, getProjects, isFixtureMode } from "@/lib/data";
import { isUnavailable, type Project } from "@/lib/types";


export const dynamic = "force-dynamic";

export const metadata = { title: "Overlaps · GridBridge" };

export default async function TimePage() {
  const [matches, projects, national] = await Promise.all([
    getMatches({ limit: 500 }), getProjects(), loadNationalExplorer({ page: 1, limit: 1 }),
  ]);
  if (isUnavailable(projects) && !national.available) {
    return (
      <main>
        <h1>Time view</h1>
        <ErrorState />
      </main>
    );
  }

  // One current record per project key, exactly as the overlap page chooses it.
  const current = new Map<string, Project>();
  for (const p of [...(isUnavailable(projects) ? [] : projects)].sort((a, b) => Number(b.active) - Number(a.active) || a._id.localeCompare(b._id))) {
    if (!current.has(p.project_key)) current.set(p.project_key, p);
  }
  const slim: TimeProject[] = [...current.values()].map((p) => ({
    key: p.project_key,
    name: p.name,
    utility: p.utility,
    owner_code: p.owner_code,
    center: p.center ? { lat: p.center.lat, lon: p.center.lon } : null,
    in_service: p.in_service,
    confidence: p.location_confidence ?? null,
    source_id: p.source.source_id,
    page: p.source.page,
  }));
  const nationalAll = national.available ? nationalTimeProjects(national.mapProjects, national.sources) : [];
  const nationalPoints = nationalAll.filter(stillPlanned);
  slim.push(...nationalPoints);
  const pairs: TimePair[] = (isUnavailable(matches) || isUnavailable(projects) ? [] : matches).map((m) => ({
    id: m._id,
    a: m.a,
    b: m.b,
    distance_mi: m.distance_mi,
    time_gap_days: m.time_gap_days,
    band: m.band,
    view: m.view,
    rank: m.rank ?? null,
    review_state: m.review_state ?? null,
  }));

  // Scope needs only names, postal codes and Census regions; counties and bounds stay on the server.
  const geography = {
    states: (national.geography?.states ?? []).map((st) => ({ fips: st.state_fips, name: st.name, usps: st.usps, region: st.census_region_code ?? "" })),
    regions: (national.geography?.regions ?? []).map((r) => ({ code: r.region_code, name: r.name })),
  };
  return (
    <TimeView projects={slim} geography={geography} pairs={pairs} analysisDate={analysisDate()} fixtureMode={isFixtureMode()} legacyAvailable={!isUnavailable(projects)} pairsAvailable={!isUnavailable(matches) && !isUnavailable(projects)}
      national={{ available: national.available, mode: national.mode, dataset: national.dataset,
        drawn: nationalPoints.length, inService: nationalAll.length - nationalPoints.length, unlocated: national.unlocatedTotal, truncated: national.mapTruncated }} />
  );
}
