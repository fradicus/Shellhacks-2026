// The one data access layer for pages. Frozen after F00.
//
// DATA_MODE=fixture: reads data/fixtures/*.json from disk (dev and CI only; never set in production).
// Otherwise: calls the same server repository the /api/* route handlers use, which reads MongoDB Atlas (F06) under one
// total deadline per read. Pages no longer fetch their own API over HTTP.
// Every function returns `Result<T>`: on any failure it returns `{unavailable: true}`, never fixtures.
//
// Server components and route handlers only. Client components get data as props, or fetch /api/* directly.

import "server-only";
import { unstable_rethrow } from "next/navigation";
import { fileIdentity, IdentityCache } from "./server/cache";
import { DbUnavailable } from "./server/db";
import { DeadlineExceeded } from "./server/deadline";
import { repository } from "./server/repository";
import type {
  Coverage,
  Extraction,
  Location,
  Match,
  MatchRow,
  PairDetail,
  Project,
  Result,
  Run,
  Source,
  View,
  VersionChange,
  Brief,
} from "./types";

export type BBox = [west: number, south: number, east: number, north: number];

export interface ProjectQuery {
  bbox?: BBox;
  view?: View;
  /** Include located endpoints (default true). List pages that never read them pass false. */
  endpoints?: boolean;
}

export interface MatchQuery {
  view?: View;
  maxDistance?: number;
  limit?: number;
}

/** Fixture mode is refused on a Vercel production deployment even if DATA_MODE is set there by mistake:
 * production then reads the API (Atlas) and shows "unavailable" rather than sample data. */
export const isFixtureMode = () => process.env.DATA_MODE === "fixture" && process.env.VERCEL_ENV !== "production";

/** Analysis date for the future/historical split. */
export function analysisDate(): string {
  return process.env.ANALYSIS_DATE ?? "2026-09-26";
}

// --- fixture mode ------------------------------------------------------------------------------------------------------

// Parsed fixture files by file identity: an edited fixture is re-read, an unchanged one is parsed once.
const fixtureFiles = new IdentityCache<unknown[]>(16);

async function fixture<T>(name: string): Promise<T[]> {
  const { readFile } = await import("node:fs/promises");
  const { join } = await import("node:path");
  const dir = process.env.FIXTURE_DIR ?? join(process.cwd(), "..", "data", "fixtures");
  const path = join(dir, `${name}.json`);
  // Callers get a shallow copy, so sorting or filtering one never reorders another's rows.
  return [...(await fixtureFiles.get(await fileIdentity(path), async () => JSON.parse(await readFile(path, "utf8"))))] as T[];
}

function inBBox(p: Project, [w, s, e, n]: BBox): boolean {
  const c = p.center;
  return !!c && c.lon >= w && c.lon <= e && c.lat >= s && c.lat <= n;
}

async function fixtureProjects(withEndpoints: boolean): Promise<Project[]> {
  const projects = await fixture<Project>("projects");
  if (!withEndpoints) return projects;
  const locations = await fixture<Location>("locations");
  return projects.map((p) => ({
    ...p,
    endpoints: locations
      .filter((l) => l.project_key === p.project_key && (l.project_id ?? p._id) === p._id)
      .sort((x, y) => x.endpoint_index - y.endpoint_index),
  }));
}

const fixtureApi = {
  async projects(q: ProjectQuery): Promise<Project[]> {
    const all = await fixtureProjects(q.endpoints !== false);
    // Same rule as /api/projects: null-center projects only when no bbox is given.
    return q.bbox ? all.filter((p) => inBBox(p, q.bbox!)) : all;
  },
  async matches(q: MatchQuery): Promise<MatchRow[]> {
    const [matches, projects] = await Promise.all([fixture<Match>("matches"), fixtureProjects(false)]);
    const byKey = new Map(projects.map((p) => [p.project_key, p]));
    return matches
      .filter((m) => !q.view || m.view === q.view)
      .filter((m) => q.maxDistance === undefined || m.distance_mi <= q.maxDistance)
      .slice(0, q.limit ?? 500)
      .map((m) => ({ ...m, project_a: byKey.get(m.a) ?? null, project_b: byKey.get(m.b) ?? null }));
  },
  async pair(id: string): Promise<PairDetail | null> {
    const [matches, projects, briefs, changes, sources] = await Promise.all([
      fixture<Match>("matches"),
      fixtureProjects(true),
      fixture<Brief>("briefs"),
      fixture<VersionChange>("version_changes"),
      fixture<Source>("sources"),
    ]);
    const match = matches.find((m) => m._id === id);
    if (!match) return null;
    const byKey = new Map(projects.map((p) => [p.project_key, p]));
    const a = byKey.get(match.a) ?? null;
    const b = byKey.get(match.b) ?? null;
    const version_changes = changes.filter((c) => c.project_key === match.a || c.project_key === match.b);
    const cited = new Set([
      ...[a, b].flatMap((p) => (p ? [p.source.source_id] : [])),
      ...version_changes.flatMap((c) => [c.from_source, c.to_source]),
    ]);
    return {
      match,
      a,
      b,
      brief: briefs.find((x) => x.match_id === id && x.validation === "passed") ?? null,
      version_changes,
      sources: sources.filter((s) => cited.has(s._id)),
    };
  },
};

// --- public API --------------------------------------------------------------------------------------------------------

async function guard<T>(what: string, fn: () => Promise<T>): Promise<Result<T>> {
  try {
    return await fn();
  } catch (err) {
    // Let Next's own control-flow errors through (e.g. the "render dynamically" bailout during build).
    unstable_rethrow(err);
    // Driver errors can carry hostnames; only the repository's own classified reasons are passed on.
    const reason = err instanceof DbUnavailable || err instanceof DeadlineExceeded ? err.message : err instanceof Error ? err.name : String(err);
    console.error(`data.${what} unavailable: ${reason}`);
    return { unavailable: true, reason: `${what}: ${reason}` };
  }
}

/** The release the legacy pages and exports read: the loader's active dataset id, or for fixtures the content hash
 * of the fixture files, so a page and its export can be shown to describe the same snapshot. */
export function getRelease(): Promise<Result<string>> {
  return guard("getRelease", async () => {
    if (!isFixtureMode()) return repository.release();
    const [{ readFile }, { join }, { createHash }] = await Promise.all([import("node:fs/promises"), import("node:path"), import("node:crypto")]);
    const dir = process.env.FIXTURE_DIR ?? join(process.cwd(), "..", "data", "fixtures");
    const hash = createHash("sha256");
    for (const name of ["projects", "matches", "locations"]) hash.update(await readFile(join(dir, `${name}.json`)));
    return `fixture-${hash.digest("hex").slice(0, 12)}`;
  });
}

export function getProjects(q: ProjectQuery = {}): Promise<Result<Project[]>> {
  return guard("getProjects", () =>
    isFixtureMode() ? fixtureApi.projects(q) : repository.projects({ bbox: q.bbox, endpoints: q.endpoints }),
  );
}

export function getMatches(q: MatchQuery = {}): Promise<Result<MatchRow[]>> {
  return guard("getMatches", () => (isFixtureMode() ? fixtureApi.matches(q) : repository.matches(q)));
}

/** null when the pair doesn't exist. */
export function getPair(id: string): Promise<Result<PairDetail | null>> {
  return guard("getPair", () => (isFixtureMode() ? fixtureApi.pair(id) : repository.pair(id)));
}

export function getVersionChanges(): Promise<Result<VersionChange[]>> {
  return guard("getVersionChanges", () => (isFixtureMode() ? fixture<VersionChange>("version_changes") : repository.versions()));
}

/** Source documents (filings), for citing names, pages and public URLs. */
export function getSources(): Promise<Result<Source[]>> {
  return guard("getSources", () => (isFixtureMode() ? fixture<Source>("sources") : repository.sources()));
}

/** Every stored brief, passed and rejected (the workbench shows rejection reasons). */
export function getBriefs(): Promise<Result<Brief[]>> {
  return guard("getBriefs", () => (isFixtureMode() ? fixture<Brief>("briefs") : repository.briefs()));
}

/** Latest pipeline run (by started_at, then _id), or null when none is stored. */
export function getLatestRun(): Promise<Result<Run | null>> {
  return guard("getLatestRun", async () => {
    if (!isFixtureMode()) return repository.latestRun();
    const runs = await fixture<Run>("runs");
    return runs.sort((a, b) => b.started_at.localeCompare(a.started_at) || b._id.localeCompare(a._id))[0] ?? null;
  });
}

export function getCoverage(): Promise<Result<Coverage[]>> {
  return guard("getCoverage", () => (isFixtureMode() ? fixture<Coverage>("coverage") : repository.coverage()));
}

export function getExtractions(q: { source?: string } = {}): Promise<Result<Extraction[]>> {
  return guard("getExtractions", async () =>
    isFixtureMode()
      ? (await fixture<Extraction>("extractions")).filter((e) => !q.source || e.source_id === q.source)
      : repository.extractions(q),
  );
}
