// The one data access layer for pages. Frozen after F00.
//
// DATA_MODE=fixture: reads data/fixtures/*.json from disk (dev and CI only; never set in production).
// Otherwise: fetches this app's own /api/* routes, which read MongoDB Atlas (F06).
// Every function returns `Result<T>`: on any failure it returns `{unavailable: true}`, never fixtures.
//
// Call it from server components and route handlers. Client components get data as props, or fetch /api/* directly.

import { unstable_rethrow } from "next/navigation";
import type {
  Coverage,
  Extraction,
  Location,
  Match,
  MatchRow,
  PairDetail,
  Project,
  Result,
  View,
  VersionChange,
  Brief,
} from "./types";

export type BBox = [west: number, south: number, east: number, north: number];

export interface ProjectQuery {
  bbox?: BBox;
  view?: View;
}

export interface MatchQuery {
  view?: View;
  maxDistance?: number;
  limit?: number;
}

export const isFixtureMode = () => process.env.DATA_MODE === "fixture";

/** Analysis date for the future/historical split. */
export function analysisDate(): string {
  return process.env.ANALYSIS_DATE ?? "2026-09-26";
}

// --- fixture mode ------------------------------------------------------------------------------------------------------

async function fixture<T>(name: string): Promise<T[]> {
  const { readFile } = await import("node:fs/promises");
  const { join } = await import("node:path");
  const dir = process.env.FIXTURE_DIR ?? join(process.cwd(), "..", "data", "fixtures");
  return JSON.parse(await readFile(join(dir, `${name}.json`), "utf8")) as T[];
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
      .filter((l) => l.project_key === p.project_key)
      .sort((x, y) => x.endpoint_index - y.endpoint_index),
  }));
}

const fixtureApi = {
  async projects(q: ProjectQuery): Promise<Project[]> {
    const all = await fixtureProjects(true);
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
    const [matches, projects, briefs, changes] = await Promise.all([
      fixture<Match>("matches"),
      fixtureProjects(true),
      fixture<Brief>("briefs"),
      fixture<VersionChange>("version_changes"),
    ]);
    const match = matches.find((m) => m._id === id);
    if (!match) return null;
    const byKey = new Map(projects.map((p) => [p.project_key, p]));
    return {
      match,
      a: byKey.get(match.a) ?? null,
      b: byKey.get(match.b) ?? null,
      brief: briefs.find((b) => b.match_id === id && b.validation === "passed") ?? null,
      version_changes: changes.filter((c) => c.project_key === match.a || c.project_key === match.b),
    };
  },
};

// --- API mode ----------------------------------------------------------------------------------------------------------

function baseUrl(): string {
  if (typeof window !== "undefined") return "";
  if (process.env.SITE_URL) return process.env.SITE_URL;
  // Production: the public domain (the per-deployment URL sits behind Vercel deployment protection).
  const host =
    process.env.VERCEL_ENV === "production" ? process.env.VERCEL_PROJECT_PRODUCTION_URL : process.env.VERCEL_URL;
  return host ? `https://${host}` : `http://localhost:${process.env.PORT ?? 3000}`;
}

async function api<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T | null> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v));
  const url = `${baseUrl()}${path}${qs.size ? `?${qs}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return (await res.json()) as T;
}

// --- public API --------------------------------------------------------------------------------------------------------

async function guard<T>(what: string, fn: () => Promise<T>): Promise<Result<T>> {
  try {
    return await fn();
  } catch (err) {
    // Let Next's own control-flow errors through (e.g. the "render dynamically" bailout during build).
    unstable_rethrow(err);
    const reason = err instanceof Error ? err.message : String(err);
    console.error(`data.${what} unavailable: ${reason}`);
    return { unavailable: true, reason: `${what}: ${reason}` };
  }
}

export function getProjects(q: ProjectQuery = {}): Promise<Result<Project[]>> {
  return guard("getProjects", async () =>
    isFixtureMode()
      ? fixtureApi.projects(q)
      : ((await api<Project[]>("/api/projects", { bbox: q.bbox?.join(","), view: q.view })) ?? []),
  );
}

export function getMatches(q: MatchQuery = {}): Promise<Result<MatchRow[]>> {
  return guard("getMatches", async () =>
    isFixtureMode()
      ? fixtureApi.matches(q)
      : ((await api<MatchRow[]>("/api/matches", { view: q.view, maxDistance: q.maxDistance, limit: q.limit })) ?? []),
  );
}

/** null when the pair doesn't exist. */
export function getPair(id: string): Promise<Result<PairDetail | null>> {
  return guard("getPair", async () =>
    isFixtureMode() ? fixtureApi.pair(id) : api<PairDetail>(`/api/pairs/${encodeURIComponent(id)}`),
  );
}

export function getVersionChanges(): Promise<Result<VersionChange[]>> {
  return guard("getVersionChanges", async () =>
    isFixtureMode() ? fixture<VersionChange>("version_changes") : ((await api<VersionChange[]>("/api/versions")) ?? []),
  );
}

export function getCoverage(): Promise<Result<Coverage[]>> {
  return guard("getCoverage", async () =>
    isFixtureMode() ? fixture<Coverage>("coverage") : ((await api<Coverage[]>("/api/coverage")) ?? []),
  );
}

export function getExtractions(q: { source?: string } = {}): Promise<Result<Extraction[]>> {
  return guard("getExtractions", async () =>
    isFixtureMode()
      ? (await fixture<Extraction>("extractions")).filter((e) => !q.source || e.source_id === q.source)
      : ((await api<Extraction[]>("/api/extraction", { source: q.source })) ?? []),
  );
}
