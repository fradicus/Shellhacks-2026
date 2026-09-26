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
const ReadEvidenceSchema = z.object({ point: PointSchema, year: z.number().int(), sample_sha256: sha, object_url: z.string(), object_etag: z.string(), index_sha256: sha, retrieved_at: z.iso.datetime({ offset: true }), object_size: z.number().int().positive(), ranges: z.array(z.object({ start: z.number().int().nonnegative(), end: z.number().int().nonnegative(), sha256: sha }).strict()).min(1).max(80), bytes_read: z.number().int().positive().max(32 * 1024 * 1024), requests: z.number().int().positive().max(80), whole_object_sha256: z.null() });
const EvidenceSchema = z.object({ schema_version: z.literal("aef-read-evidence-v2"), snapshot_sha256: sha, records: z.array(ReadEvidenceSchema).max(500) });
export type AEFSnapshot = z.infer<typeof SnapshotSchema> & { evidence: z.infer<typeof ReadEvidenceSchema>[] };
export function validateSnapshot(value: unknown, evidenceValue: unknown): AEFSnapshot {
  const snapshot = SnapshotSchema.parse(value); const seen = new Set<string>();
  const evidence = EvidenceSchema.parse(evidenceValue);
  if (evidence.records.length !== snapshot.records.length) throw new Error("Missing AEF per-record read evidence");
  for (const record of snapshot.records) {
    const id = `${record.point.lat},${record.point.lon},${record.year}`;
    if (seen.has(id)) throw new Error("Duplicate AEF point/year"); seen.add(id);
    if (!record.object_url.includes(`/annual/${record.year}/`)) throw new Error("AEF year mismatch");
    const bytes = Buffer.from(record.raw.map((x) => x & 255));
    if (createHash("sha256").update(bytes).digest("hex") !== record.sample_sha256) throw new Error("AEF sample hash mismatch");
    for (let i = 0; i < 64; i++) if (Math.abs(record.embedding[i] - Math.sign(record.raw[i]) * (record.raw[i] / 127.5) ** 2) > 1e-12) throw new Error("Invalid AEF decoding");
    const matches = evidence.records.filter((e) => e.point.lat === record.point.lat && e.point.lon === record.point.lon && e.year === record.year);
    const read = matches[0];
    if (matches.length !== 1 || read.object_url !== record.object_url || read.object_etag !== record.object_etag || read.index_sha256 !== record.index_sha256 || read.sample_sha256 !== record.sample_sha256) throw new Error("AEF read evidence binding mismatch");
    if (Date.parse(read.retrieved_at) > Date.now() + 300000 || read.ranges.some((r) => r.end < r.start || r.end >= read.object_size) || read.ranges.reduce((n, r) => n + r.end - r.start + 1, 0) !== read.bytes_read || read.requests !== read.ranges.length) throw new Error("AEF read evidence limits/identity invalid");
  }
  return { ...snapshot, evidence: evidence.records };
}
export async function readSnapshot(): Promise<AEFSnapshot | null> {
  try {
    const path = resolve(process.cwd(), "..", "data", "environment", "aef-samples.json");
    if ((await stat(path)).size > 2_000_000) return null;
    const text = await readFile(path, "utf8");
    if (Buffer.byteLength(text) > 2_000_000) return null;
    const evidencePath = path.replace(/\.json$/, ".evidence.json");
    if ((await stat(evidencePath)).size > 4_000_000) return null;
    const evidenceText = await readFile(evidencePath, "utf8");
    if (Buffer.byteLength(evidenceText) > 4_000_000) return null;
    const evidence = JSON.parse(evidenceText);
    const hash = createHash("sha256").update(text.replace(/\r\n/g, "\n")).digest("hex");
    if (evidence.snapshot_sha256 !== hash) return null;
    const snapshot = validateSnapshot(JSON.parse(text), evidence);
    if (Date.parse(snapshot.generated_at) > Date.now() + 300000) return null;
    return snapshot;
  } catch { return null; }
}
export function aef(point: Point, year: number, snapshot: AEFSnapshot | null, now = new Date()): Envelope<AEFData> {
  const result = empty<AEFData>("aef", { ...point, year }, "Annual satellite embedding; not current weather, soil strength or a site approval.", "unavailable", now);
  const match = snapshot?.records.find((r) => r.point.lat === point.lat && r.point.lon === point.lon && r.year === year);
  if (!match) { result.limitations.push("No validated artifact matches this exact point and year."); return result; }
  const read = snapshot!.evidence.find((e) => e.point.lat === point.lat && e.point.lon === point.lon && e.year === year)!;
  result.retrieved_at = new Date(read.retrieved_at).toISOString();
  result.status = "available"; result.source_version = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL";
  result.evidence_hash = match.sample_sha256; result.data = { scope: "annual_satellite_embedding", samples: [match as AEFSample] };
  result.valid_from = `${year}-01-01T00:00:00Z`; result.valid_to = `${year + 1}-01-01T00:00:00Z`;
  result.coverage = { requested: 1, completed: 1, failed: 0, truncated: false }; return result;
}
