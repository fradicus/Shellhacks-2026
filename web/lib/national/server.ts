import "server-only";

import { displayPoints } from "./locations";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { Db, Document, Filter } from "mongodb";
import { getDb } from "@/lib/server/db";
import { filterNationalProjects, MAX_DATASET_PROJECTS, MAX_EXPORT, MAX_MAP_POINTS, validateGeographyFilters } from "./filters";
import type {
  NationalCoverage,
  NationalExplorerPayload,
  NationalFilters,
  NationalGeography,
  NationalProject,
  NationalReference,
  NationalSource,
  NationalStatus,
} from "./types";

const DATA_DIR = resolve(process.cwd(), "..", "data", "national");
const SOURCE_LIMIT = 2_000;
const FACET_LIMIT = 500;
const QUERY_TIMEOUT_MS = 5_000;

class NationalUnavailable extends Error {}

const snapshotEnabled = () => process.env.NATIONAL_DATA_MODE === "snapshot" && process.env.VERCEL_ENV !== "production";
const snapshotRejected = () => process.env.NATIONAL_DATA_MODE === "snapshot" && process.env.VERCEL_ENV === "production";

async function jsonFile<T>(name: string): Promise<T> {
  return JSON.parse(await readFile(resolve(DATA_DIR, name), "utf8")) as T;
}

function validGeography(value: unknown): value is NationalGeography {
  const item = value as Partial<NationalGeography> | null;
  return !!item && item.schema_version === "national-geography-v1" && Array.isArray(item.states) && Array.isArray(item.counties);
}

function validSources(value: unknown): value is NationalSource[] {
  return Array.isArray(value) && value.every((raw) => {
    const item = raw as Partial<NationalSource> | null;
    return !!item && typeof item._id === "string" && typeof item.title === "string" && typeof item.publisher === "string"
      && Array.isArray(item.states) && item.states.every((code) => /^\d{2}$/.test(code))
      && Array.isArray(item.notes) && item.notes.every((note) => typeof note === "string");
  });
}

function validProjects(value: unknown): value is NationalProject[] {
  const statuses = new Set(["planned", "under_construction", "proposed", "in_service", "cancelled", "unknown"]);
  return Array.isArray(value) && value.every((raw) => {
    const item = raw as Partial<NationalProject> | null;
    const center = item?.center;
    const centerValid = center === null || (!!center && Number.isFinite(center.lat) && Number.isFinite(center.lon)
      && center.lat >= -90 && center.lat <= 90 && center.lon >= -180 && center.lon <= 180);
    return !!item && typeof item._id === "string" && typeof item.source_id === "string" && typeof item.name === "string"
      && Array.isArray(item.states) && item.states.every((code) => /^\d{2}$/.test(code))
      && Array.isArray(item.counties) && item.counties.every((code) => /^\d{5}$/.test(code))
      && typeof item.status_group === "string" && statuses.has(item.status_group)
      && !!item.in_service && ["day", "month", "year", "unknown"].includes(item.in_service.precision)
      && (!item.approximate_location || (center === null && Array.isArray(item.approximate_location.anchors)
        && item.approximate_location.anchors.length > 0
        && displayPoints(item as NationalProject).length === item.approximate_location.anchors.length))
      && !!item.evidence && item.evidence.raw !== null && typeof item.evidence.raw === "object" && !Array.isArray(item.evidence.raw) && centerValid;
  });
}

function validCoverage(value: unknown): value is NationalCoverage {
  const item = value as Partial<NationalCoverage> | null;
  return !!item && item.schema_version === "national-coverage-v1" && Number.isInteger(item.projects_total) && Array.isArray(item.sources);
}

export async function loadNationalReference(): Promise<NationalReference> {
  try {
    const [geography, sources, coverage] = await Promise.all([
      jsonFile<unknown>("geography.json"), jsonFile<unknown>("sources.json"), jsonFile<unknown>("coverage.json"),
    ]);
    if (!validGeography(geography) || !validSources(sources)) throw new Error("published reference files failed their public shape check");
    return { geography, sources, coverage: validCoverage(coverage) ? coverage : null, referenceAvailable: true };
  } catch (error) {
    return {
      geography: null, sources: [], coverage: null, referenceAvailable: false,
      reason: `National reference catalog unavailable (${error instanceof Error ? error.message : "read error"}).`,
    };
  }
}

function clean<T>(doc: Document): T {
  const rest = { ...doc };
  const { id } = rest;
  if (typeof id !== "string") throw new NationalUnavailable("national record is missing its public id");
  delete rest._id;
  delete rest.id;
  delete rest.dataset;
  return { ...rest, _id: id } as T;
}

async function activeNationalDb(): Promise<{ db: Db; dataset: string }> {
  const db = await getDb();
  const pointer = await db.collection<{ _id: string; dataset?: string }>("meta").findOne({ _id: "national_active" }, { maxTimeMS: QUERY_TIMEOUT_MS });
  if (!pointer?.dataset) throw new NationalUnavailable("no active national dataset loaded");
  return { db, dataset: pointer.dataset };
}

const escapeRegex = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function dateClause(filters: NationalFilters): Document | null {
  if (!filters.from && !filters.to) return null;
  const branch = (precision: "day" | "month" | "year", size: number) => {
    const range: Document = {};
    if (filters.from) range.$gte = filters.from.slice(0, size);
    if (filters.to) range.$lte = filters.to.slice(0, size);
    return { "in_service.precision": precision, "in_service.value": range };
  };
  return { $or: [branch("day", 10), branch("month", 7), branch("year", 4)] };
}

function mongoFilter(filters: NationalFilters, geography: NationalGeography | null, dataset: string): Filter<Document> {
  const clauses: Document[] = [{ dataset }];
  if (filters.region) {
    const states = geography?.states.filter((item) => item.census_region_code === filters.region).map((item) => item.state_fips) ?? [];
    clauses.push({ states: { $in: states } });
  }
  if (filters.state) clauses.push({ states: filters.state });
  if (filters.county) clauses.push({ counties: filters.county });
  if (filters.planningRegion) clauses.push({ planning_region: filters.planningRegion });
  if (filters.owner) clauses.push({ $or: [{ owner: filters.owner }, { other_owners: filters.owner }] });
  if (filters.status) clauses.push({ status_group: filters.status });
  const date = dateClause(filters);
  if (date) clauses.push(date);
  if (filters.text) {
    const literal = { $regex: escapeRegex(filters.text), $options: "i" };
    clauses.push({
      $or: [
        { name: literal }, { native_id: literal }, { description: literal },
        { owner: literal }, { planning_region: literal }, { status: literal },
      ],
    });
  }
  return { $and: clauses };
}

const locatedFilter = (base: Filter<Document>): Filter<Document> => ({
  $and: [base, { center: { $type: "object" } }, { "center.lat": { $type: "number" } }, { "center.lon": { $type: "number" } }],
});

const approximateFilter = (base: Filter<Document>): Filter<Document> => ({
  $and: [base, { center: null, location_review: { $ne: "rejected" },
    "approximate_location.precision": "county", "approximate_location.eligible_for_matching": false,
    "approximate_location.reference_source.url": { $type: "string" },
    "approximate_location.anchors": { $elemMatch: {
      lat: { $type: "number", $gte: -90, $lte: 90 }, lon: { $type: "number", $gte: -180, $lte: 180 },
      county_geoid: { $type: "string" },
    } },
  }],
});
const displayFilter = (base: Filter<Document>): Filter<Document> => ({ $or: [locatedFilter(base), approximateFilter(base)] });

async function facets(db: Db, dataset: string) {
  const grouped = async (pipeline: Document[]) => {
    const rows = await db.collection("national_projects").aggregate<{ _id: string }>([
      { $match: { dataset } }, ...pipeline, { $group: { _id: "$value" } }, { $sort: { _id: 1 } }, { $limit: FACET_LIMIT + 1 },
    ]).maxTimeMS(QUERY_TIMEOUT_MS).toArray();
    if (rows.length > FACET_LIMIT) throw new NationalUnavailable("national filter catalog exceeds its safety bound");
    return rows.map((row) => row._id).filter((value) => typeof value === "string" && value.length > 0);
  };
  const [planningRegions, owners, statuses] = await Promise.all([
    grouped([{ $match: { planning_region: { $type: "string", $ne: "" } } }, { $project: { value: "$planning_region" } }]),
    grouped([
      { $project: { values: { $setUnion: [{ $cond: [{ $eq: [{ $type: "$owner" }, "string"] }, ["$owner"], []] }, { $ifNull: ["$other_owners", []] }] } } },
      { $unwind: "$values" }, { $project: { value: "$values" } },
    ]),
    grouped([{ $match: { status_group: { $type: "string" } } }, { $project: { value: "$status_group" } }]),
  ]);
  return { planningRegions, owners, statuses: statuses as NationalStatus[] };
}

// One large map payload per warm instance; keep the active pointer outside the cache.
// Cold instances still load from Atlas. A shared cache is only needed if cold starts dominate.
let mapCache: { dataset: string; expires: number; pending: ReturnType<typeof queryDataset> } | undefined;

async function atlasQuery(filters: NationalFilters, geography: NationalGeography | null) {
  const { db, dataset } = await activeNationalDb();
  // Only the unfiltered request used by /time and /history. New filter keys bypass by default.
  const isMapRequest = filters.page === 1 && filters.limit === 1
    && Object.keys(filters).every((key) => key === "page" || key === "limit");
  if (!isMapRequest) return queryDataset(db, dataset, filters, geography);
  if (!mapCache || mapCache.dataset !== dataset || mapCache.expires <= Date.now()) {
    const entry = { dataset, expires: Date.now() + 5 * 60_000, pending: queryDataset(db, dataset, filters, geography) };
    mapCache = entry;
    entry.pending.catch(() => {
      // An older failed fill must not evict a newer dataset's result.
      if (mapCache === entry) mapCache = undefined;
    });
  }
  return mapCache.pending;
}

async function queryDataset(db: Db, dataset: string, filters: NationalFilters, geography: NationalGeography | null) {
  const filter = mongoFilter(filters, geography, dataset);
  const offset = (filters.page - 1) * filters.limit;
  const [total, locatedTotal, approximateTotal, projectDocs, mapDocs, sourceDocs, run, filterFacets] = await Promise.all([
    db.collection("national_projects").countDocuments(filter, { maxTimeMS: QUERY_TIMEOUT_MS }),
    db.collection("national_projects").countDocuments(locatedFilter(filter), { maxTimeMS: QUERY_TIMEOUT_MS }),
    db.collection("national_projects").countDocuments(approximateFilter(filter), { maxTimeMS: QUERY_TIMEOUT_MS }),
    db.collection("national_projects").find(filter).sort({ id: 1 }).skip(offset).limit(filters.limit).maxTimeMS(QUERY_TIMEOUT_MS).toArray(),
    db.collection("national_projects").find(displayFilter(filter)).sort({ id: 1 }).limit(MAX_MAP_POINTS + 1).maxTimeMS(QUERY_TIMEOUT_MS).toArray(),
    db.collection("national_sources").find({ dataset }).sort({ id: 1 }).limit(SOURCE_LIMIT + 1).maxTimeMS(QUERY_TIMEOUT_MS).toArray(),
    db.collection("national_runs").findOne({ dataset }, { sort: { finished_at: -1, _id: -1 }, maxTimeMS: QUERY_TIMEOUT_MS }),
    facets(db, dataset),
  ]);
  if (sourceDocs.length > SOURCE_LIMIT) throw new NationalUnavailable("active national source catalog exceeds the explorer safety bound");
  const projects = projectDocs.map((doc) => clean<NationalProject>(doc));
  const mapProjects = mapDocs.slice(0, MAX_MAP_POINTS).map((doc) => clean<NationalProject>(doc));
  const sources = sourceDocs.map((doc) => clean<NationalSource>(doc));
  if (!validProjects(projects) || !validProjects(mapProjects) || !validSources(sources)) throw new NationalUnavailable("active national records failed their public shape check");
  const candidate = run?.coverage ?? run?.counts?.coverage ?? null;
  return {
    dataset, projects, mapProjects, sources, total, locatedTotal, approximateTotal,
    mapTruncated: mapDocs.length > MAX_MAP_POINTS,
    coverage: validCoverage(candidate) ? candidate : null,
    facets: filterFacets,
  };
}

async function fileSnapshot() {
  const [projects, sources, coverage] = await Promise.all([
    jsonFile<unknown>("projects.json"), jsonFile<unknown>("sources.json"), jsonFile<unknown>("coverage.json"),
  ]);
  if (!validProjects(projects) || !validSources(sources) || !validCoverage(coverage)) {
    throw new NationalUnavailable("committed national snapshot failed its public shape check");
  }
  if (projects.length > MAX_DATASET_PROJECTS || sources.length > SOURCE_LIMIT) {
    throw new NationalUnavailable("committed national snapshot exceeds the explorer safety bound");
  }
  return { dataset: "committed-snapshot", projects, sources, coverage };
}

function unavailable(reference: NationalReference, filters: NationalFilters, reason: string, invalidQuery = false): NationalExplorerPayload {
  return {
    ...reference, available: false, mode: "unavailable", dataset: null, reason, filters,
    projects: [], mapProjects: [], total: 0, locatedTotal: 0, approximateTotal: 0, unlocatedTotal: 0,
    page: filters.page, limit: filters.limit, mapTruncated: false,
    facets: { planningRegions: [], owners: [], statuses: [] }, invalidQuery,
  };
}

const values = (items: (string | null)[]) => [...new Set(items.filter((item): item is string => !!item))].sort((a, b) => a.localeCompare(b));

export async function loadNationalExplorer(filters: NationalFilters): Promise<NationalExplorerPayload> {
  const reference = await loadNationalReference();
  const geographyIssue = validateGeographyFilters(filters, reference.geography);
  if (geographyIssue) return unavailable(reference, filters, geographyIssue, reference.geography !== null);
  if (snapshotRejected()) return unavailable(reference, filters, "Committed national project snapshots are disabled in production.");
  try {
    if (snapshotEnabled()) {
      const source = await fileSnapshot();
      const filtered = filterNationalProjects(source.projects, filters, reference.geography);
      const located = filtered.filter((project) => project.center !== null);
      const mapped = filtered.filter((project) => displayPoints(project).length > 0);
      const approximateTotal = mapped.filter((project) => project.center === null).length;
      const offset = (filters.page - 1) * filters.limit;
      return {
        ...reference, sources: source.sources, coverage: source.coverage,
        available: true, mode: "snapshot", dataset: source.dataset, filters,
        projects: filtered.slice(offset, offset + filters.limit), mapProjects: mapped.slice(0, MAX_MAP_POINTS),
        total: filtered.length, locatedTotal: located.length, approximateTotal, unlocatedTotal: filtered.length - located.length - approximateTotal,
        page: filters.page, limit: filters.limit, mapTruncated: mapped.length > MAX_MAP_POINTS,
        facets: {
          planningRegions: values(source.projects.map((project) => project.planning_region)),
          owners: values(source.projects.flatMap((project) => [project.owner, ...project.other_owners])),
          statuses: [...new Set(source.projects.map((project) => project.status_group))].sort(),
        },
      };
    }
    const source = await atlasQuery(filters, reference.geography);
    return {
      ...reference, sources: source.sources, coverage: source.coverage,
      available: true, mode: "atlas", dataset: source.dataset, filters,
      projects: source.projects, mapProjects: source.mapProjects,
      total: source.total, locatedTotal: source.locatedTotal, approximateTotal: source.approximateTotal,
      unlocatedTotal: source.total - source.locatedTotal - source.approximateTotal,
      page: filters.page, limit: filters.limit, mapTruncated: source.mapTruncated, facets: source.facets,
    };
  } catch (error) {
    const reason = error instanceof NationalUnavailable ? error.message : "national database unavailable";
    return unavailable(reference, filters, reason);
  }
}

export async function loadNationalExport(filters: NationalFilters): Promise<NationalExplorerPayload> {
  const reference = await loadNationalReference();
  const geographyIssue = validateGeographyFilters(filters, reference.geography);
  if (geographyIssue) return unavailable(reference, filters, geographyIssue, reference.geography !== null);
  if (snapshotRejected()) return unavailable(reference, filters, "Committed national project snapshots are disabled in production.");
  try {
    let projects: NationalProject[];
    let sources: NationalSource[];
    let coverage: NationalCoverage | null;
    let dataset: string;
    let mode: "atlas" | "snapshot";
    if (snapshotEnabled()) {
      const source = await fileSnapshot();
      projects = filterNationalProjects(source.projects, filters, reference.geography).slice(0, MAX_EXPORT + 1);
      ({ sources, coverage, dataset } = source);
      mode = "snapshot";
    } else {
      const active = await activeNationalDb();
      dataset = active.dataset;
      const filter = mongoFilter(filters, reference.geography, dataset);
      const [docs, sourceDocs, run] = await Promise.all([
        active.db.collection("national_projects").find(filter).sort({ id: 1 }).limit(MAX_EXPORT + 1).maxTimeMS(QUERY_TIMEOUT_MS).toArray(),
        active.db.collection("national_sources").find({ dataset }).sort({ id: 1 }).limit(SOURCE_LIMIT + 1).maxTimeMS(QUERY_TIMEOUT_MS).toArray(),
        active.db.collection("national_runs").findOne({ dataset }, { sort: { finished_at: -1, _id: -1 }, maxTimeMS: QUERY_TIMEOUT_MS }),
      ]);
      projects = docs.map((doc) => clean<NationalProject>(doc));
      sources = sourceDocs.map((doc) => clean<NationalSource>(doc));
      const candidate = run?.coverage ?? run?.counts?.coverage ?? null;
      coverage = validCoverage(candidate) ? candidate : null;
      mode = "atlas";
    }
    if (projects.length > MAX_EXPORT) return unavailable(reference, filters, `Export is limited to ${MAX_EXPORT.toLocaleString("en-US")} filtered records.`);
    const located = projects.filter((project) => project.center !== null);
    const approximateTotal = projects.filter((project) => project.center === null && displayPoints(project).length > 0).length;
    return {
      ...reference, sources, coverage, available: true, mode, dataset, filters,
      projects, mapProjects: [], total: projects.length, locatedTotal: located.length,
      approximateTotal, unlocatedTotal: projects.length - located.length - approximateTotal, page: 1, limit: projects.length,
      mapTruncated: false, facets: { planningRegions: [], owners: [], statuses: [] },
    };
  } catch (error) {
    return unavailable(reference, filters, error instanceof NationalUnavailable ? error.message : "national database unavailable");
  }
}
