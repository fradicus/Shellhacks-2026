import "server-only";
import { z } from "zod";
import { getDb } from "@/lib/server/db";
import { projectSummary } from "@/lib/national/summaries";
import type { NationalProject } from "@/lib/national/types";
import type { CandidatePage } from "./types";
import { PAGE_SIZE, RULE, pairFilter, type PairQuery } from "./query";

const TIMEOUT = 5000;
const pair = z.object({
  id: z.string().regex(/^npc:[a-f0-9]{32}$/), a: z.string().min(1), b: z.string().min(1),
  distance_mi: z.number().min(0).lt(25), time_gap_days: z.number().int().min(0).nullable(),
  band: z.union([z.literal(0), z.literal(1)]), rank: z.number().int().positive(),
  tier: z.enum(["confirmed", "official", "tentative"]), rule_version: z.literal(RULE),
  identity_version: z.string().min(1),
});
export class PairReadError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

export async function loadCandidatePairs(query: PairQuery): Promise<CandidatePage> {
  if (process.env.NATIONAL_DATA_MODE === "snapshot") {
    throw new PairReadError(503, "Nearby candidates require a published dataset; snapshot pairs are unavailable.");
  }
  const db = await getDb();
  const options = { maxTimeMS: TIMEOUT };
  const active = await db.collection("meta").findOne({ _id: "national_active" as never }, options);
  if (!active?.dataset) throw new PairReadError(503, "National project data is unavailable.");
  if (active.dataset !== query.dataset) throw new PairReadError(409, "The published dataset changed. Refresh the page to see matching candidates.");
  const run = await db.collection("national_runs").findOne({ dataset: query.dataset, status: { $in: ["ok", "ready"] } }, options);
  if (!Number.isInteger(run?.counts?.national_candidate_pairs)) {
    throw new PairReadError(503, "Nearby candidates have not been published for this dataset yet.");
  }
  const filter = pairFilter(query);
  const [total, docs] = await Promise.all([
    db.collection("national_candidate_pairs").countDocuments(filter, options),
    db.collection("national_candidate_pairs").find(filter).sort({ rank: 1, id: 1 })
      .skip(query.offset).limit(query.id ? 1 : PAGE_SIZE).maxTimeMS(TIMEOUT).toArray(),
  ]);
  if (query.id && !docs.length) throw new PairReadError(404, "This candidate pair was not found in the displayed dataset.");
  const pairs = docs.map(doc => pair.parse(doc));
  const ids = [...new Set(pairs.flatMap(p => [p.a, p.b]))];
  const projects = ids.length ? await db.collection("national_projects").find({ dataset: query.dataset, id: { $in: ids } })
    .limit(PAGE_SIZE * 2).maxTimeMS(TIMEOUT).toArray() : [];
  if (projects.length !== ids.length || projects.some(p => typeof p.id !== "string" || !p.center
    || !Number.isFinite(p.center.lat) || !Number.isFinite(p.center.lon))) {
    throw new PairReadError(503, "Candidate project references are incomplete. Please retry.");
  }
  return { available: true, dataset: query.dataset, pairs,
    projects: projects.map(p => projectSummary({ ...p, _id: p.id } as unknown as NationalProject)),
    total, offset: query.offset, nextOffset: query.offset + pairs.length < total ? query.offset + pairs.length : null };
}
