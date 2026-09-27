import "server-only";

// The one server-side read path for the legacy dataset, shared by route handlers and by `lib/data.ts` for pages.
// Pages used to fetch this app's own /api/* over HTTP; both now call these functions directly, so a page and the
// route it mirrors cannot drift, and neither pays a network round trip or an unbounded wait.
import type { Db } from "mongodb";
import type { BBox } from "./http";
import { activeDataset, DbUnavailable, getDb } from "./db";
import { withDeadline } from "./deadline";
import * as q from "./queries";
import type { ReadOptions } from "./queries";
import type { View } from "@/lib/types";

/** Total budget for one read, however many queries it issues. */
export const READ_DEADLINE_MS = 8_000;
/** List reads stop here and fail loudly: a page never shows a silently truncated list. */
export const MAX_LIST = 5_000;

export class ResultTooLarge extends DbUnavailable {}

async function atlas<T>(label: string, work: (db: Db, dataset: string, read: ReadOptions) => Promise<T>, signal?: AbortSignal): Promise<T> {
  return withDeadline(label, READ_DEADLINE_MS, async (inner) => {
    const db = await getDb();
    const dataset = await activeDataset(db, inner);
    return work(db, dataset, { signal: inner });
  }, signal);
}

async function bounded<T>(label: string, rows: Promise<T[]>): Promise<T[]> {
  const out = await rows;
  if (out.length > MAX_LIST) throw new ResultTooLarge(`${label} exceeds the ${MAX_LIST.toLocaleString("en-US")}-row read bound`);
  return out;
}

export interface ProjectRead {
  bbox?: BBox;
  keys?: string[];
  /** Include located endpoints (default true, the /api/projects contract). List pages pass false. */
  endpoints?: boolean;
}

export interface MatchRead {
  view?: View;
  maxDistance?: number;
  project?: string;
  pair?: string;
  limit?: number;
  skip?: number;
}

export const repository = {
  /** The active release id (the dataset the loader last activated). */
  release: (signal?: AbortSignal) => atlas("release", async (_db, dataset) => dataset, signal),

  projects: (r: ProjectRead = {}, signal?: AbortSignal) =>
    atlas("projects", (db, dataset, read) => bounded("projects", q.projects(db, dataset, { ...r, limit: MAX_LIST + 1 }, read)), signal),

  /** One page of projects plus the filtered total, for exports that page through the complete result. */
  projectPage: (r: ProjectRead & { limit: number; skip: number }, signal?: AbortSignal) =>
    atlas("project page", async (db, dataset, read) => {
      const [rows, total] = await Promise.all([q.projects(db, dataset, r, read), q.projectCount(db, dataset, r, read)]);
      return { dataset, rows, total };
    }, signal),

  matches: (r: MatchRead = {}, signal?: AbortSignal) =>
    atlas("matches", (db, dataset, read) => q.matches(db, dataset, r, read), signal),

  matchPage: (r: MatchRead & { limit: number; skip: number }, signal?: AbortSignal) =>
    atlas("match page", async (db, dataset, read) => {
      const [rows, total] = await Promise.all([q.matches(db, dataset, r, read), q.matchCount(db, dataset, r, read)]);
      return { dataset, rows, total };
    }, signal),

  pair: (id: string, signal?: AbortSignal) => atlas("pair", (db, dataset, read) => q.pair(db, dataset, id, read), signal),
  versions: (signal?: AbortSignal) => atlas("versions", (db, dataset, read) => bounded("versions", q.versions(db, dataset, read)), signal),
  sources: (signal?: AbortSignal) => atlas("sources", (db, dataset, read) => bounded("sources", q.sources(db, dataset, read)), signal),
  coverage: (signal?: AbortSignal) => atlas("coverage", (db, dataset, read) => q.coverage(db, dataset, read), signal),
  briefs: (signal?: AbortSignal) => atlas("briefs", (db, dataset, read) => bounded("briefs", q.briefs(db, dataset, read)), signal),
  extractions: (r: { source?: string } = {}, signal?: AbortSignal) =>
    atlas("extractions", (db, dataset, read) => bounded("extractions", q.extractions(db, dataset, r, read)), signal),

  /** Runs are not dataset-scoped, so this does not require an active release. */
  latestRun: (signal?: AbortSignal) =>
    withDeadline("latest run", READ_DEADLINE_MS, async (inner) => q.latestRun(await getDb(), { signal: inner }), signal),
};
