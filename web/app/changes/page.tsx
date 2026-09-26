import { ChangesView } from "@/components/changes/ChangesView";
import { ErrorState } from "@/components/ui";
import { analysisDate, getMatches, getProjects, getSources, getVersionChanges } from "@/lib/data";
import { isUnavailable } from "@/lib/types";

export const metadata = { title: "Filing changes · GridBridge" };

export default async function ChangesPage() {
  const [changes, sources, projects, matches] = await Promise.all([
    getVersionChanges(),
    getSources(),
    getProjects(),
    getMatches({ limit: 500 }),
  ]);
  if (isUnavailable(changes) || isUnavailable(sources) || isUnavailable(projects) || isUnavailable(matches)) {
    return (
      <main>
        <h1>Filing changes</h1>
        <ErrorState />
      </main>
    );
  }
  // Latest filing's record wins for the display name; any record will do for utility.
  const names: Record<string, { name: string; utility: string }> = {};
  for (const p of [...projects].sort((a, b) => Number(a.active) - Number(b.active))) {
    names[p.project_key] = { name: p.name, utility: p.utility };
  }
  const inMatches: Record<string, string[]> = {};
  for (const m of matches) for (const k of [m.a, m.b]) (inMatches[k] ??= []).push(m._id);
  return (
    <ChangesView changes={changes} sources={sources} names={names} inMatches={inMatches} analysisDate={analysisDate()} />
  );
}
