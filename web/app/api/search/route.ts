import type { Db } from "mongodb";
import { z } from "zod";
import { DbUnavailable } from "@/lib/server/db";
import { handle } from "@/lib/server/http";

export const dynamic = "force-dynamic";

const QUERY = z.strictObject({
  q: z.string().trim().min(1).max(500).optional(),
  ref_id: z.string().trim().min(1).max(300).optional(),
  k: z.coerce.number().int().min(1).max(50).default(10),
});

const EMBED_MODEL = process.env.GEMINI_EMBED_MODEL ?? "gemini-embedding-001";
// Keep in sync with pipeline/embeddings DIMENSIONS and pipeline/load VECTOR_DIMENSIONS.
const EMBED_DIMENSIONS = 768;
const VECTOR_INDEX = "embedding_vector";

interface Hit {
  id: string;
  kind: "match" | "project" | "brief";
  ref_id: string;
  text: string;
  score?: number;
  rank?: number;
}

interface NeighborDoc {
  ref_id: string;
  neighbors: { ref_id: string; kind: Hit["kind"]; score: number; rank: number }[];
}

/** Query-time embedding is the site's only live Gemini call (specs/decisions/F20-live-query-embedding.md). */
async function embedQuery(q: string): Promise<number[]> {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new DbUnavailable("query embedding not configured");
  const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${EMBED_MODEL}:embedContent`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-goog-api-key": key },
    body: JSON.stringify({ content: { parts: [{ text: q }] }, outputDimensionality: EMBED_DIMENSIONS }),
    cache: "no-store",
  });
  if (!res.ok) throw new DbUnavailable(`query embedding failed (${res.status})`);
  const body = (await res.json()) as { embedding?: { values?: number[] } };
  const values = body.embedding?.values;
  if (!values?.length) throw new DbUnavailable("query embedding returned no vector");
  return values;
}

async function searchByText(db: Db, dataset: string, q: string, k: number): Promise<Hit[]> {
  const queryVector = await embedQuery(q);
  return db
    .collection("embeddings")
    .aggregate<Hit>([
      {
        $vectorSearch: {
          index: VECTOR_INDEX,
          path: "vector",
          queryVector,
          numCandidates: Math.max(k * 10, 50),
          limit: k,
          filter: { dataset },
        },
      },
      { $project: { _id: 0, id: 1, kind: 1, ref_id: 1, text: 1, score: { $meta: "vectorSearchScore" } } },
    ])
    .toArray();
}

/** Precomputed neighbors: stored at embed time, so this mode never calls Gemini. */
async function neighborsOf(db: Db, dataset: string, refId: string, k: number): Promise<Hit[] | null> {
  const doc = await db.collection<NeighborDoc>("neighbors").findOne({ dataset, ref_id: refId });
  if (!doc) return null;
  const top = doc.neighbors.slice(0, k);
  const texts = await db
    .collection("embeddings")
    .find({ dataset, ref_id: { $in: top.map((n) => n.ref_id) } })
    .project<Pick<Hit, "id" | "kind" | "ref_id" | "text">>({ _id: 0, id: 1, kind: 1, ref_id: 1, text: 1 })
    .toArray();
  const byRef = new Map(texts.map((t) => [t.ref_id, t]));
  return top.map((n) => ({
    id: byRef.get(n.ref_id)?.id ?? `emb:${n.kind}:${n.ref_id}`,
    kind: n.kind,
    ref_id: n.ref_id,
    text: byRef.get(n.ref_id)?.text ?? "",
    score: n.score,
    rank: n.rank,
  }));
}

export function GET(req: Request) {
  return handle(req, QUERY, async ({ q, ref_id, k }, db, dataset) => {
    if (q) {
      return { mode: "search", q, model: EMBED_MODEL, results: await searchByText(db, dataset, q, k) };
    }
    if (ref_id) {
      const results = await neighborsOf(db, dataset, ref_id, k);
      return results === null ? null : { mode: "neighbors", ref_id, results };
    }
    return { error: "pass exactly one of q or ref_id" };
  });
}
