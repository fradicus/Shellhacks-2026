import "server-only";

import { analysisDate, getProjects, getSources, getVersionChanges, isFixtureMode } from "@/lib/data";
import { loadNationalExplorer } from "@/lib/national/server";
import { isUnavailable, type Project } from "@/lib/types";
import { nationalTier } from "@/components/time/nationalProjects";
import { legacyHistory, nationalHistory, type HistoryProject } from "./events";

export interface HistoryPayload {
  projects: HistoryProject[];
  analysisDate: string;
  fixtureMode: boolean;
  legacyAvailable: boolean;
  national: { available: boolean; mode: string; dataset: string | null; unlocated: number; truncated: boolean; reason: string | null };
}

/** Reads through the same loaders as /time: legacy filings and the active national dataset. No new query or copy. */
export async function loadHistory(): Promise<HistoryPayload> {
  const [projects, changes, sources, national] = await Promise.all([
    getProjects(), getVersionChanges(), getSources(), loadNationalExplorer({ page: 1, limit: 1 }),
  ]);
  const out: HistoryProject[] = [];
  if (!isUnavailable(projects)) {
    // One current record per project key, chosen exactly as the overlap page chooses it.
    const current = new Map<string, Project>();
    for (const p of [...projects].sort((a, b) => Number(b.active) - Number(a.active) || a._id.localeCompare(b._id)))
      if (!current.has(p.project_key)) current.set(p.project_key, p);
    const bySource = new Map((isUnavailable(sources) ? [] : sources).map((s) => [s._id, s]));
    const versionRows = isUnavailable(changes) ? [] : changes;
    for (const p of current.values()) out.push(legacyHistory(p, versionRows, bySource));
  }
  if (national.available) {
    const bySource = new Map(national.sources.map((s) => [s._id, s]));
    // The points /time draws (confirmed or labeled candidate); legacy projections are already covered above.
    for (const p of national.mapProjects) {
      const tier = p._id.startsWith("legacy:") || !p.center ? null : nationalTier(p);
      if (tier) out.push({ ...nationalHistory(p, bySource.get(p.source_id)), tier });
    }
  }
  return {
    projects: out,
    analysisDate: analysisDate(),
    fixtureMode: isFixtureMode(),
    legacyAvailable: !isUnavailable(projects),
    national: {
      available: national.available,
      mode: national.mode,
      dataset: national.dataset,
      unlocated: national.available ? national.unlocatedTotal : 0,
      truncated: national.mapTruncated,
      reason: national.available ? null : (national.reason ?? null),
    },
  };
}
