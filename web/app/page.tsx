import { OverlapExplorer } from "@/components/map/OverlapExplorer";
import { ErrorState } from "@/components/ui";
import { analysisDate, getMatches, getProjects, isFixtureMode } from "@/lib/data";
import { isUnavailable, type View } from "@/lib/types";

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

  const counts = Object.fromEntries(VIEWS.map((v) => [v, matches.filter((m) => m.view === v).length])) as Record<
    View,
    number
  >;
  // Future is the planner's default; if it's empty, open the first view that has results (and say so).
  const initialView = VIEWS.find((v) => counts[v] > 0) ?? "future";
  const sources = [...new Set(projects.map((p) => p.source.source_id))].sort();

  return (
    <OverlapExplorer
      matches={matches}
      projects={projects}
      counts={counts}
      initialView={initialView}
      analysisDate={analysisDate()}
      sources={sources}
      fixtureMode={isFixtureMode()}
    />
  );
}
