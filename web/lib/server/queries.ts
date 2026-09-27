// Read queries against the active dataset. Every document is stored as {_id: "<dataset>:<id>", id, dataset, ...};
// `clean` maps it back to the record shape in lib/types.ts.
import type { Db, Document, Filter } from "mongodb";
import type { BBox } from "./http";
import type {
  Brief,
  Coverage,
  Extraction,
  Match,
  MatchRow,
  PairDetail,
  Project,
  Review,
  Run,
  Source,
  VersionChange,
  View,
} from "@/lib/types";

type Stored = Document & { id: string; dataset: string };

/** Per-call read options: every query carries a server-side time limit and, when given, the caller's abort signal. */
export interface ReadOptions {
  signal?: AbortSignal;
  maxTimeMS?: number;
}

const QUERY_TIMEOUT_MS = 5_000;

function clean<T>(doc: Stored): T {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { _id, id, dataset, ...rest } = doc;
  return { ...rest, _id: id } as T;
}

const find = async <T>(
  db: Db,
  coll: string,
  filter: Filter<Document>,
  opts: { sort?: Document; limit?: number; skip?: number; projection?: Document } = {},
  read: ReadOptions = {},
) =>
  (await db.collection(coll).find(filter, { ...opts, maxTimeMS: read.maxTimeMS ?? QUERY_TIMEOUT_MS, signal: read.signal }).toArray())
    .map((d) => clean<T>(d as unknown as Stored));

const count = (db: Db, coll: string, filter: Filter<Document>, read: ReadOptions = {}) =>
  db.collection(coll).countDocuments(filter, { maxTimeMS: read.maxTimeMS ?? QUERY_TIMEOUT_MS, signal: read.signal });

function projectFilter(dataset: string, q: { bbox?: BBox; keys?: string[] }): Filter<Document> {
  const filter: Filter<Document> = { dataset };
  if (q.keys) filter.project_key = { $in: q.keys };
  if (q.bbox) {
    const [w, s, e, n] = q.bbox;
    // Viewport query on the 2dsphere-indexed GeoJSON center. Null-center projects only appear without a bbox.
    filter.geo = {
      $geoWithin: { $geometry: { type: "Polygon", coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } },
    };
  }
  return filter;
}

/** Project records, every filing version. `endpoints: false` leaves out the located endpoints, which only the pair
 * evidence reads; `limit`/`skip` page through them in `project_key, id` order. */
export function projects(
  db: Db,
  dataset: string,
  q: { bbox?: BBox; keys?: string[]; endpoints?: boolean; limit?: number; skip?: number },
  read: ReadOptions = {},
): Promise<Project[]> {
  return find<Project>(db, "projects", projectFilter(dataset, q), {
    sort: { project_key: 1, id: 1 },
    projection: q.endpoints === false ? { endpoints: 0 } : undefined,
    limit: q.limit,
    skip: q.skip || undefined,
  }, read);
}

export const projectCount = (db: Db, dataset: string, q: { bbox?: BBox; keys?: string[] }, read: ReadOptions = {}) =>
  count(db, "projects", projectFilter(dataset, q), read);

/** One project per key: the active filing's record (falls back to any record for that key). */
async function projectsByKey(db: Db, dataset: string, keys: string[], withEndpoints: boolean, read: ReadOptions = {}): Promise<Map<string, Project>> {
  const docs = await find<Project>(db, "projects", { dataset, project_key: { $in: keys } }, {
    projection: withEndpoints ? undefined : { endpoints: 0 },
    sort: { active: -1, id: 1 },
  }, read);
  const out = new Map<string, Project>();
  for (const p of docs) if (!out.has(p.project_key)) out.set(p.project_key, p);
  return out;
}

function matchFilter(dataset: string, q: { view?: View; maxDistance?: number; project?: string; pair?: string }): Filter<Document> {
  const filter: Filter<Document> = { dataset };
  if (q.view) filter.view = q.view;
  if (q.maxDistance !== undefined) filter.distance_mi = { $lte: q.maxDistance };
  if (q.project) filter.$or = [{ a: q.project }, { b: q.project }];
  if (q.pair) filter.id = q.pair;
  return filter;
}

export async function matches(
  db: Db,
  dataset: string,
  q: { view?: View; maxDistance?: number; project?: string; pair?: string; limit?: number; skip?: number },
  read: ReadOptions = {},
): Promise<MatchRow[]> {
  const rows = await find<Match>(db, "matches", matchFilter(dataset, q), { sort: { rank: 1, id: 1 }, limit: q.limit ?? 500, skip: q.skip || undefined }, read);
  const byKey = await projectsByKey(db, dataset, [...new Set(rows.flatMap((m) => [m.a, m.b]))], false, read);
  return rows.map((m) => ({ ...m, project_a: byKey.get(m.a) ?? null, project_b: byKey.get(m.b) ?? null }));
}

export const matchCount = (db: Db, dataset: string, q: { view?: View; maxDistance?: number; project?: string; pair?: string }, read: ReadOptions = {}) =>
  count(db, "matches", matchFilter(dataset, q), read);

export async function pair(db: Db, dataset: string, id: string, read: ReadOptions = {}): Promise<PairDetail | null> {
  const [match] = await find<Match>(db, "matches", { dataset, id }, { limit: 1 }, read);
  if (!match) return null;
  const [byKey, briefs, versionChanges, reviews] = await Promise.all([
    projectsByKey(db, dataset, [match.a, match.b], true, read),
    find<Brief>(db, "briefs", { dataset, match_id: id, validation: "passed" }, { sort: { generated_at: -1 }, limit: 1 }, read),
    find<VersionChange>(db, "version_changes", { dataset, project_key: { $in: [match.a, match.b] } }, { sort: { id: 1 } }, read),
    find<Review>(db, "reviews", { dataset, record_id: id }, { sort: { at: 1 } }, read),
  ]);
  const a = byKey.get(match.a) ?? null;
  const b = byKey.get(match.b) ?? null;
  const cited = [
    ...new Set([
      ...[a, b].flatMap((p) => (p ? [p.source.source_id] : [])),
      ...versionChanges.flatMap((c) => [c.from_source, c.to_source]),
    ]),
  ];
  const sources = await find<Source>(db, "sources", { dataset, id: { $in: cited } }, { sort: { id: 1 } }, read);
  return { match, a, b, brief: briefs[0] ?? null, version_changes: versionChanges, reviews, sources };
}

export const versions = (db: Db, dataset: string, read: ReadOptions = {}) =>
  find<VersionChange>(db, "version_changes", { dataset }, { sort: { project_key: 1, id: 1 } }, read);

export const sources = (db: Db, dataset: string, read: ReadOptions = {}) =>
  find<Source>(db, "sources", { dataset }, { sort: { id: 1 } }, read);

export const coverage = (db: Db, dataset: string, read: ReadOptions = {}) =>
  find<Coverage>(db, "coverage", { dataset }, { sort: { id: 1 } }, read);

/** Every brief, passed and rejected (stale or unverified passed briefs are stored as rejected by the loader). */
export const briefs = (db: Db, dataset: string, read: ReadOptions = {}) =>
  find<Brief>(db, "briefs", { dataset }, { sort: { match_id: 1, generated_at: 1, id: 1 } }, read);

/**
 * The latest run of any dataset. Runs aren't dataset-namespaced (`_id: load:<sha>`), so they're read as stored, and
 * only the public Run fields: never `errors`, which can hold exception text.
 */
export const latestRun = (db: Db, read: ReadOptions = {}) =>
  db.collection<Run>("runs").findOne(
    {},
    {
      sort: { started_at: -1, _id: -1 },
      projection: { _id: 1, stage: 1, started_at: 1, finished_at: 1, status: 1, counts: 1, dataset: 1 },
      maxTimeMS: read.maxTimeMS ?? QUERY_TIMEOUT_MS,
      signal: read.signal,
    },
  );

export const extractions = (db: Db, dataset: string, q: { source?: string }, read: ReadOptions = {}) =>
  find<Extraction>(db, "extractions", q.source ? { dataset, source_id: q.source } : { dataset }, {
    sort: { source_id: 1, page: 1 },
  }, read);
