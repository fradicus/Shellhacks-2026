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
  Source,
  VersionChange,
  View,
} from "@/lib/types";

type Stored = Document & { id: string; dataset: string };

function clean<T>(doc: Stored): T {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { _id, id, dataset, ...rest } = doc;
  return { ...rest, _id: id } as T;
}

const find = async <T>(db: Db, coll: string, filter: Filter<Document>, opts: { sort?: Document; limit?: number; projection?: Document } = {}) =>
  (await db.collection(coll).find(filter, opts).toArray()).map((d) => clean<T>(d as unknown as Stored));

export function projects(db: Db, dataset: string, q: { bbox?: BBox }): Promise<Project[]> {
  const filter: Filter<Document> = { dataset };
  if (q.bbox) {
    const [w, s, e, n] = q.bbox;
    // Viewport query on the 2dsphere-indexed GeoJSON center. Null-center projects only appear without a bbox.
    filter.geo = {
      $geoWithin: { $geometry: { type: "Polygon", coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } },
    };
  }
  return find<Project>(db, "projects", filter, { sort: { project_key: 1, id: 1 } });
}

/** One project per key: the active filing's record (falls back to any record for that key). */
async function projectsByKey(db: Db, dataset: string, keys: string[], withEndpoints: boolean): Promise<Map<string, Project>> {
  const docs = await find<Project>(db, "projects", { dataset, project_key: { $in: keys } }, {
    projection: withEndpoints ? undefined : { endpoints: 0 },
    sort: { active: -1, id: 1 },
  });
  const out = new Map<string, Project>();
  for (const p of docs) if (!out.has(p.project_key)) out.set(p.project_key, p);
  return out;
}

export async function matches(
  db: Db,
  dataset: string,
  q: { view?: View; maxDistance?: number; limit?: number },
): Promise<MatchRow[]> {
  const filter: Filter<Document> = { dataset };
  if (q.view) filter.view = q.view;
  if (q.maxDistance !== undefined) filter.distance_mi = { $lte: q.maxDistance };
  const rows = await find<Match>(db, "matches", filter, { sort: { rank: 1, id: 1 }, limit: q.limit ?? 500 });
  const byKey = await projectsByKey(db, dataset, [...new Set(rows.flatMap((m) => [m.a, m.b]))], false);
  return rows.map((m) => ({ ...m, project_a: byKey.get(m.a) ?? null, project_b: byKey.get(m.b) ?? null }));
}

export async function pair(db: Db, dataset: string, id: string): Promise<PairDetail | null> {
  const [match] = await find<Match>(db, "matches", { dataset, id }, { limit: 1 });
  if (!match) return null;
  const [byKey, briefs, versionChanges, reviews] = await Promise.all([
    projectsByKey(db, dataset, [match.a, match.b], true),
    find<Brief>(db, "briefs", { dataset, match_id: id, validation: "passed" }, { sort: { generated_at: -1 }, limit: 1 }),
    find<VersionChange>(db, "version_changes", { dataset, project_key: { $in: [match.a, match.b] } }, { sort: { id: 1 } }),
    find<Review>(db, "reviews", { dataset, record_id: id }, { sort: { at: 1 } }),
  ]);
  const a = byKey.get(match.a) ?? null;
  const b = byKey.get(match.b) ?? null;
  const cited = [
    ...new Set([
      ...[a, b].flatMap((p) => (p ? [p.source.source_id] : [])),
      ...versionChanges.flatMap((c) => [c.from_source, c.to_source]),
    ]),
  ];
  const sources = await find<Source>(db, "sources", { dataset, id: { $in: cited } }, { sort: { id: 1 } });
  return { match, a, b, brief: briefs[0] ?? null, version_changes: versionChanges, reviews, sources };
}

export const versions = (db: Db, dataset: string) =>
  find<VersionChange>(db, "version_changes", { dataset }, { sort: { project_key: 1, id: 1 } });

export const sources = (db: Db, dataset: string) => find<Source>(db, "sources", { dataset }, { sort: { id: 1 } });

export const coverage =(db: Db, dataset: string) => find<Coverage>(db, "coverage", { dataset }, { sort: { id: 1 } });

export const extractions = (db: Db, dataset: string, q: { source?: string }) =>
  find<Extraction>(db, "extractions", q.source ? { dataset, source_id: q.source } : { dataset }, {
    sort: { source_id: 1, page: 1 },
  });
