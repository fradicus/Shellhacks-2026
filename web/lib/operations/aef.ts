import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { z } from "zod";
import { PointSchema, type Point, type AEFData, type AEFSample, type Envelope } from "./contracts";
import { empty } from "./providers";

export const ATTRIBUTION = "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind.";
const sha = z.string().regex(/^[a-f0-9]{64}$/);
const RecordSchema = z.object({
  point: PointSchema, year: z.number().int().min(2017).max(2100), object_url: z.string().url().refine((s) => /^https:\/\/storage\.googleapis\.com\/alphaearth_foundations\/satellite_embedding\/v1\/annual\/\d{4}\//.test(s)), object_etag: z.string().min(1),
  index_sha256: sha, sample_sha256: sha, crs: z.string().regex(/^EPSG:32[67]\d{2}$/), row: z.number().int().nonnegative(), col: z.number().int().nonnegative(), pixel_size_m: z.literal(10),
  raw: z.array(z.number().int().min(-127).max(127)).length(64), embedding: z.array(z.number().finite().min(-1).max(1)).length(64), attribution: z.literal(ATTRIBUTION),
}).strict();
export const SnapshotSchema = z.object({ schema_version: z.literal("aef-point-v1"), generated_at: z.iso.datetime(), records: z.array(RecordSchema).max(500) }).strict();
export type AEFSnapshot = z.infer<typeof SnapshotSchema>;
export function validateSnapshot(value: unknown): AEFSnapshot {
  const snapshot = SnapshotSchema.parse(value); const seen = new Set<string>();
  for (const record of snapshot.records) {
    const id = `${record.point.lat},${record.point.lon},${record.year}`;
    if (seen.has(id)) throw new Error("Duplicate AEF point/year"); seen.add(id);
    if (!record.object_url.includes(`/annual/${record.year}/`)) throw new Error("AEF year mismatch");
    const bytes = Buffer.from(record.raw.map((x) => x & 255));
    if (createHash("sha256").update(bytes).digest("hex") !== record.sample_sha256) throw new Error("AEF sample hash mismatch");
    for (let i = 0; i < 64; i++) if (Math.abs(record.embedding[i] - Math.sign(record.raw[i]) * (record.raw[i] / 127.5) ** 2) > 1e-12) throw new Error("Invalid AEF decoding");
  }
  return snapshot;
}
export async function readSnapshot(): Promise<AEFSnapshot | null> {
  try {
    const path = resolve(process.cwd(), "..", "data", "environment", "aef-samples.json");
    if ((await stat(path)).size > 2_000_000) return null;
    const text = await readFile(path, "utf8");
    if (Buffer.byteLength(text) > 2_000_000) return null;
    const evidencePath = path.replace(/\.json$/, ".evidence.json");
    if ((await stat(evidencePath)).size > 256000) return null;
    const evidenceText = await readFile(evidencePath, "utf8");
    if (Buffer.byteLength(evidenceText) > 256000) return null;
    const evidence = JSON.parse(evidenceText);
    const hash = createHash("sha256").update(text.replace(/\r\n/g, "\n")).digest("hex");
    if (evidence.snapshot_sha256 !== hash) return null;
    const snapshot = validateSnapshot(JSON.parse(text));
    if (Date.parse(snapshot.generated_at) > Date.now() + 300000) return null;
    return snapshot;
  } catch { return null; }
}
export function aef(point: Point, year: number, snapshot: AEFSnapshot | null, now = new Date()): Envelope<AEFData> {
  const result = empty<AEFData>("aef", { ...point, year }, "Annual satellite embedding; not current weather, soil strength or a site approval.", "unavailable", now);
  const match = snapshot?.records.find((r) => r.point.lat === point.lat && r.point.lon === point.lon && r.year === year);
  if (!match) { result.limitations.push("No validated artifact matches this exact point and year."); return result; }
  result.status = "available"; result.source_version = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL";
  result.evidence_hash = match.sample_sha256; result.data = { scope: "annual_satellite_embedding", samples: [match as AEFSample] };
  result.valid_from = `${year}-01-01T00:00:00Z`; result.valid_to = `${year + 1}-01-01T00:00:00Z`;
  result.coverage = { requested: 1, completed: 1, failed: 0, truncated: false }; return result;
}
