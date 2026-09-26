import { OverlapExplorer } from "@/components/map/OverlapExplorer";
import { ErrorState } from "@/components/ui";
import { analysisDate, getMatches, getProjects, isFixtureMode } from "@/lib/data";
import { isUnavailable, type Project, type View } from "@/lib/types";

const VIEWS: View[] = ["future", "historical", "tentative"];

export default async function Home() {
  const [matches, projects] = await Promise.all([getMatches({ limit: 500 }), getProjects()]);

  if (isUnavailable(matches) || isUnavailable(projects)) {
    return (
      <main>
        <h1>Transmission overlaps</h1>
        <ErrorState />
      </main>
    );
  }

  // One current record per project key: the active filing's (ties or none -> smallest _id), so an older filing's
  // version never shows up as a second current project. Older versions stay on /changes and in the pair evidence.
  const current = new Map<string, Project>();
  for (const p of [...projects].sort((a, b) => Number(b.active) - Number(a.active) || a._id.localeCompare(b._id))) {
    if (!current.has(p.project_key)) current.set(p.project_key, p);
  }
  const superseded = projects.length - current.size;

  const counts = Object.fromEntries(VIEWS.map((v) => [v, matches.filter((m) => m.view === v).length])) as Record<
    View,
    number
  >;
  // Future is the planner's default; if it's empty, open the first view that has results (and say so).
  const initialView = VIEWS.find((v) => counts[v] > 0) ?? "future";
  const sources = [...new Set(projects.map((p) => p.source.source_id))].sort();
  const currentProjects = [...current.values()];

  return (
    <OverlapExplorer
      matches={matches}
      projects={currentProjects}
      superseded={superseded}
      counts={counts}
      initialView={initialView}
      analysisDate={analysisDate()}
      sources={sources}
      fixtureMode={isFixtureMode()}
    />
  );
}
